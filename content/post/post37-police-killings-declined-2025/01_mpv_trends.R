# ==============================================================================
# MPV Police Violence Trends: National, State, and Agency Analysis
# ==============================================================================
#
# Author:   Justin Nix
# Source:   Mapping Police Violence (MPVDatasetDownload.xlsx)
#           Campaign Zero / mappingpoliceviolence.org
#
# Purpose:
#   Analyze MPV 2013-2025 incident-level data to describe national, state, and
#   agency-level trends in fatal police violence. Responds to Stateline/MPV
#   reporting (April 2026) that police killings may have declined in 2025.
#   Produces figures and pre-computed outputs for a public blog post.
#
# Data:
#   Download MPVDatasetDownload.xlsx from:
#   https://mappingpoliceviolence.us/s/MPVDatasetDownload.xlsx
#   Place it in the project root directory before running this script.
#
# Inputs:
#   - MPVDatasetDownload.xlsx (Sheet 1: incident data, Sheet 3: state data)
#
# Outputs (saved to output/):
#   - mpv_annual_national.rds  -- national annual counts 2013-2025
#   - mpv_annual_state.rds     -- state annual counts + rates
#   - mpv_annual_agency.rds    -- agency annual counts (qualifying agencies)
#   - trend_results_state.rds  -- state-level regression results
#   - trend_results_agency.rds -- agency-level regression results
#
# Outputs (saved to figures/):
#   - fig1_national_trend.png  -- national annual trend line
#   - fig2_state_trends_map.png -- map of state trend direction
#   - fig3_state_multiples.png -- small multiples for notable states
#   - fig4_agency_multiples.png -- small multiples for notable agencies
#
# Runtime: ~2 min
# ==============================================================================

set.seed(20260402)

# ==============================================================================
# 0. Setup
# ==============================================================================

library(here)
library(readxl)
library(dplyr)
library(tidyr)
library(lubridate)
library(stringr)
library(ggplot2)
library(purrr)
library(broom)
library(scales)
library(maps)

dir.create(here("output"), recursive = TRUE, showWarnings = FALSE)
dir.create(here("figures"), recursive = TRUE, showWarnings = FALSE)

# Color palette (UNO red + supporting colors)
primary_color   <- "#D00000"  # UNO red
secondary_color <- "#4A4A4A"  # charcoal
accent_color    <- "#F5A623"  # amber
positive_color  <- "#2E7D32"  # improvement = green
negative_color  <- "#C62828"  # worsening = red
neutral_color   <- "#78909C"  # flat trend = slate

theme_mpv <- function(base_size = 12) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.title    = element_text(face = "bold", size = base_size + 1),
      plot.subtitle = element_text(color = secondary_color, size = base_size - 1),
      plot.caption  = element_text(color = neutral_color, size = base_size - 3, hjust = 0),
      panel.grid.minor  = element_blank(),
      legend.position   = "bottom",
      strip.text        = element_text(face = "bold", size = base_size - 1)
    )
}

# Federal agency pattern — excluded from agency-level trend analysis
# (these agencies operate nationally, not locally, making trends uninterpretable)
federal_pattern <- paste0(
  "^U\\.S\\. |^United States |^Federal Bureau|^U\\.S\\. Bureau|",
  "^Bureau of Alcohol|^Bureau of Indian|^Drug Enforcement|",
  "^U\\.S\\. Marshals|^U\\.S\\. Customs|^U\\.S\\. Border|",
  "^U\\.S\\. Immigration|^U\\.S\\. Secret|^U\\.S\\. Postal|",
  "^Transportation Security|^U\\.S\\. Fish|^U\\.S\\. Forest|",
  "^National Park Service|^U\\.S\\. Park|^U\\.S\\. Army|",
  "^U\\.S\\. Air Force|^U\\.S\\. Navy|^U\\.S\\. Marine|",
  "^Central Intelligence|^Homeland Security",
  collapse = ""
)

# ==============================================================================
# 1. Load Data
# ==============================================================================

message("Loading MPV incident data...")

raw <- read_excel(
  here("MPVDatasetDownload.xlsx"),
  sheet = "2013-2026 Police Killings"
)

state_sheet <- read_excel(
  here("MPVDatasetDownload.xlsx"),
  sheet = "2013-2026 Killings by State"
)

message(sprintf("Raw data: %d rows loaded.", nrow(raw)))

# ==============================================================================
# 2. Clean and Filter
# ==============================================================================

message("Cleaning and filtering...")

df <- raw |>
  janitor::clean_names() |>
  rename(
    date_raw       = date_of_incident_month_day_year,
    agency_raw     = agency_responsible_for_death,
    off_duty       = off_duty_killing,
    state          = state
  ) |>
  mutate(
    # Parse date and extract year
    date = as.Date(date_raw),
    year = as.integer(format(date, "%Y")),
    # Normalize case on key fields
    off_duty_norm  = str_to_upper(str_trim(off_duty)),
    state_norm     = str_to_upper(str_trim(state))
  )

# -- Exclude off-duty killings -------------------------------------------------
n_before_offd   <- nrow(df)
off_duty_mask   <- str_detect(df$off_duty_norm, "OFF-DUTY") & !is.na(df$off_duty_norm)
n_off_duty      <- sum(off_duty_mask)
df              <- df[!off_duty_mask, ]
message(sprintf("Off-duty exclusion: %d records removed (%.1f%% of raw data).",
                n_off_duty, 100 * n_off_duty / n_before_offd))

# -- Restrict to 2013-2025 (exclude partial 2026) -----------------------------
df_2026 <- df |> filter(year == 2026)
n_2026  <- nrow(df_2026)
df      <- df |> filter(year >= 2013, year <= 2025)
message(sprintf("2026 partial-year records excluded: %d (available for reference only).", n_2026))
message(sprintf("Final analysis dataset: %d records, 2013-2025.", nrow(df)))

# -- Extract primary agency (first agency listed, comma-delimited) -------------
df <- df |>
  mutate(
    agency_primary = str_trim(str_extract(agency_raw, "^[^,]+")),
    # Flag federal agencies for exclusion from agency-level analysis
    is_federal = str_detect(agency_primary, regex(federal_pattern, ignore_case = FALSE))
  )

# Normalize known mid-study agency renames to preserve longitudinal continuity
# San Bernardino County Sheriff was renamed from "Department" to "Office" in mid-2023;
# collapsing to the earlier name avoids a spurious spike in the "Office" series.
df <- df |>
  mutate(
    agency_primary = case_when(
      agency_primary == "San Bernardino County Sheriff's Office" ~
        "San Bernardino County Sheriff's Department",
      TRUE ~ agency_primary
    )
  )

# Spot check: how many multi-agency records?
n_multi_agency <- sum(str_detect(df$agency_raw, ","), na.rm = TRUE)
message(sprintf("Multi-agency records (first agency used): %d", n_multi_agency))

# ==============================================================================
# 3. National Annual Counts
# ==============================================================================

message("Computing national annual counts...")

national_annual <- df |>
  group_by(year) |>
  summarise(
    n_killed    = n(),
    .groups     = "drop"
  ) |>
  arrange(year)

# Note documented count discrepancy for 2025
mpv_published_2025 <- 1314L
our_count_2025     <- national_annual$n_killed[national_annual$year == 2025]
message(sprintf(
  "2025 count: our dataset = %d; MPV published = %d (gap = %d, %.1f%% — reflects living-database lag).",
  our_count_2025, mpv_published_2025,
  mpv_published_2025 - our_count_2025,
  100 * (mpv_published_2025 - our_count_2025) / mpv_published_2025
))

saveRDS(national_annual, here("output", "mpv_annual_national.rds"))

# ==============================================================================
# 4. State Annual Counts and Rates
# ==============================================================================

message("Computing state annual counts and rates...")

# Extract annual state population estimates from Sheet 3
# Columns named "YYYY ACS Population" (2013-2024; 2025 not available)
pop_cols <- grep("ACS Population", names(state_sheet), value = TRUE)
state_pop <- state_sheet |>
  janitor::clean_names() |>
  select(state, matches("acs_population")) |>
  rename_with(~ str_extract(.x, "\\d{4}"), matches("acs_population")) |>
  pivot_longer(-state, names_to = "year", values_to = "population") |>
  mutate(year = as.integer(year)) |>
  # For 2025, carry forward 2024 population (no ACS estimate yet)
  bind_rows(
    state_sheet |>
      janitor::clean_names() |>
      select(state) |>
      mutate(year = 2025L,
             population = state_sheet |>
               janitor::clean_names() |>
               pull(x2024_acs_population))
  )

# State annual killing counts
state_annual_counts <- df |>
  group_by(state_norm, year) |>
  summarise(n_killed = n(), .groups = "drop") |>
  rename(state = state_norm)

# State abbreviation join: state_pop uses 2-letter state abbreviations
state_annual <- state_annual_counts |>
  left_join(state_pop, by = c("state", "year")) |>
  mutate(
    rate_per_100k = (n_killed / population) * 100000
  )

saveRDS(state_annual, here("output", "mpv_annual_state.rds"))

# ==============================================================================
# 5. Agency Annual Counts
# ==============================================================================

message("Computing agency annual counts...")

# Filter to on-duty, non-federal agencies with >= 20 killings over 2013-2025
agency_totals <- df |>
  filter(!is_federal, !is.na(agency_primary)) |>
  group_by(agency_primary) |>
  summarise(total_killed = n(), .groups = "drop") |>
  filter(total_killed >= 20) |>
  arrange(desc(total_killed))

message(sprintf("Agencies with >= 20 killings (2013-2025): %d", nrow(agency_totals)))

# Annual counts for qualifying agencies, zero-fill missing years
all_years <- 2013:2025

agency_annual <- df |>
  filter(!is_federal, agency_primary %in% agency_totals$agency_primary) |>
  group_by(agency_primary, year) |>
  summarise(n_killed = n(), .groups = "drop") |>
  complete(agency_primary, year = all_years, fill = list(n_killed = 0L))

saveRDS(agency_annual, here("output", "mpv_annual_agency.rds"))

# ==============================================================================
# 6. Trend Analysis — States
# ==============================================================================

message("Fitting state-level trend models...")

# Use rate per 100k for cross-state comparability
# States without reliable population estimates (e.g., territories) get NA rates
state_trend_data <- state_annual |>
  filter(!is.na(rate_per_100k), !is.na(population), year >= 2013, year <= 2025)

trend_results_state <- state_trend_data |>
  group_by(state) |>
  filter(n() >= 8) |>   # require at least 8 years of data
  group_modify(~ broom::tidy(lm(rate_per_100k ~ year, data = .x))) |>
  filter(term == "year") |>
  select(state, slope = estimate, se = std.error, p_value = p.value) |>
  mutate(
    # Use raw slope direction for map (p-value thresholds suppress too many states
    # given 13-year windows and small-state noise; blog will note this limitation)
    direction = case_when(
      slope < 0  ~ "Improving",
      slope >= 0 ~ "Worsening"
    ),
    # Statistical significance flag (p < .10)
    sig = p_value < 0.10
  ) |>
  arrange(slope) |>
  ungroup()

message(sprintf(
  "State trends — Improving (negative slope): %d, Worsening (positive slope): %d",
  sum(trend_results_state$direction == "Improving"),
  sum(trend_results_state$direction == "Worsening")
))
message(sprintf(
  "State trends — Statistically significant (p < .10): %d of %d",
  sum(trend_results_state$sig, na.rm = TRUE), nrow(trend_results_state)
))

saveRDS(trend_results_state, here("output", "trend_results_state.rds"))

# ==============================================================================
# 7. Trend Analysis — Agencies
# ==============================================================================

message("Fitting agency-level trend models...")

trend_results_agency <- agency_annual |>
  group_by(agency_primary) |>
  group_modify(~ broom::tidy(lm(n_killed ~ year, data = .x))) |>
  filter(term == "year") |>
  select(agency_primary, slope = estimate, se = std.error, p_value = p.value) |>
  arrange(slope) |>
  ungroup()

saveRDS(trend_results_agency, here("output", "trend_results_agency.rds"))

# Top 10 declining and top 10 increasing agencies
top_declining <- trend_results_agency |>
  slice_min(slope, n = 10)

top_increasing <- trend_results_agency |>
  slice_max(slope, n = 10)

message("Top 10 declining agencies:")
print(top_declining |> select(agency_primary, slope, p_value))

message("Top 10 increasing agencies:")
print(top_increasing |> select(agency_primary, slope, p_value))

# ==============================================================================
# 8. Figure 1 — National Annual Trend
# ==============================================================================

message("Generating Figure 1: National annual trend...")

avg_2013_2024 <- mean(national_annual$n_killed[national_annual$year <= 2024])

fig1 <- ggplot(national_annual, aes(x = year, y = n_killed)) +
  geom_hline(yintercept = avg_2013_2024, linetype = "dashed",
             color = neutral_color, linewidth = 0.7) +
  annotate("text", x = 2013.2, y = avg_2013_2024 + 20,
           label = sprintf("2013–2024 avg: %d", round(avg_2013_2024)),
           hjust = 0, size = 3, color = neutral_color) +
  geom_line(color = primary_color, linewidth = 1.2) +
  geom_point(
    aes(fill = ifelse(year == 2025, "2025", "other")),
    size = 3, shape = 21, color = "white", stroke = 0.8,
    show.legend = FALSE
  ) +
  scale_fill_manual(values = c("2025" = accent_color, "other" = primary_color)) +
  annotate("text", x = 2025.1, y = our_count_2025 + 35,
           label = "1,173", hjust = 0, size = 3, color = secondary_color) +
  scale_x_continuous(breaks = 2013:2025, labels = 2013:2025) +
  scale_y_continuous(labels = comma, limits = c(800, 1350)) +
  theme_mpv() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1)) +
  labs(
    title    = "Fatal Police Violence in the United States, 2013–2025",
    subtitle = "All causes; on-duty officers only; primary agency only where multiple listed",
    x        = NULL,
    y        = "People killed by police",
    caption  = "Source: Mapping Police Violence (mappingpoliceviolence.org), downloaded April 2026."
  )

ggsave(here("figures", "fig1_national_trend.png"),
       fig1, width = 6.5, height = 4, dpi = 300)

# ==============================================================================
# 9. Figure 2 — State Trends Map
# ==============================================================================

message("Generating Figure 2: State trends map...")

# Map state abbreviations to full names for ggplot maps
state_abbrev_map <- tibble(
  state = state.abb,
  region = str_to_lower(state.name)
)

map_data_states <- map_data("state")

trend_map_data <- trend_results_state |>
  left_join(state_abbrev_map, by = "state") |>
  right_join(map_data_states, by = "region")

fig2 <- ggplot(trend_map_data, aes(x = long, y = lat, group = group, fill = direction)) +
  geom_polygon(color = "white", linewidth = 0.3) +
  scale_fill_manual(
    values = c(
      "Improving" = positive_color,
      "Worsening" = negative_color
    ),
    na.value = "#E0E0E0",
    na.translate = FALSE,
    name = "Rate trend\n(2013–2025)",
    labels = c("Improving" = "Declining rate", "Worsening" = "Rising rate")
  ) +
  coord_fixed(1.3) +
  theme_mpv() +
  theme(
    axis.text    = element_blank(),
    axis.ticks   = element_blank(),
    panel.grid   = element_blank(),
    legend.position = "right"
  ) +
  labs(
    title    = "Direction of Fatal Police Violence Rate Trends by State, 2013–2025",
    subtitle = "Rate per 100,000 residents; OLS slope direction (most trends are small/noisy — see text)",
    x = NULL, y = NULL,
    caption  = "Contiguous 48 states shown; AK, HI, and DC excluded. Source: Mapping Police Violence; ACS population estimates."
  )

ggsave(here("figures", "fig2_state_trends_map.png"),
       fig2, width = 6.5, height = 4, dpi = 300)

# ==============================================================================
# 10. Figure 3 — State Small Multiples (top 5 improving + top 5 worsening)
# ==============================================================================

message("Generating Figure 3: State small multiples...")

# Pick top 5 improving and top 5 worsening (among US states only, excluding DC/territories)
us_states_only <- state.abb

notable_states <- bind_rows(
  trend_results_state |>
    filter(state %in% us_states_only) |>
    slice_min(slope, n = 5) |>
    mutate(panel_group = "5 States with Largest Rate Decline"),
  trend_results_state |>
    filter(state %in% us_states_only) |>
    slice_max(slope, n = 5) |>
    mutate(panel_group = "5 States with Largest Rate Increase")
)

notable_state_abbrevs <- notable_states$state

plot_state_data <- state_trend_data |>
  filter(state %in% notable_state_abbrevs) |>
  left_join(notable_states |> select(state, slope, direction, panel_group), by = "state") |>
  mutate(
    fill_color = ifelse(direction == "Improving", positive_color, negative_color),
    state_label = state
  )

fig3 <- ggplot(plot_state_data, aes(x = year, y = rate_per_100k, color = direction)) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 1.5) +
  geom_smooth(method = "lm", se = FALSE, linetype = "dashed",
              linewidth = 0.6, alpha = 0.6) +
  scale_color_manual(
    values = c("Improving" = positive_color, "Worsening" = negative_color),
    guide = "none"
  ) +
  scale_x_continuous(breaks = c(2013, 2017, 2021, 2025)) +
  facet_wrap(~ state_label, ncol = 5, scales = "free_y") +
  theme_mpv(base_size = 10) +
  theme(
    strip.background = element_rect(fill = "#F5F5F5", color = NA),
    axis.text.x = element_text(angle = 45, hjust = 1, size = 7)
  ) +
  labs(
    title    = "Fatal Police Violence Rate: Most Improving and Worsening States",
    subtitle = "Rate per 100,000 residents; dashed line = OLS trend",
    x        = NULL,
    y        = "Killings per 100k residents",
    caption  = "Source: Mapping Police Violence; ACS population estimates."
  )

ggsave(here("figures", "fig3_state_multiples.png"),
       fig3, width = 6.5, height = 4, dpi = 300)

# ==============================================================================
# 11. Figure 4 — Agency Small Multiples (top 10 declining + top 10 increasing)
# ==============================================================================

message("Generating Figure 4: Agency small multiples...")

notable_agencies <- bind_rows(
  top_declining |> mutate(panel_group = "Declining Agencies"),
  top_increasing |> mutate(panel_group = "Increasing Agencies")
)

plot_agency_data <- agency_annual |>
  filter(agency_primary %in% notable_agencies$agency_primary) |>
  left_join(notable_agencies |> select(agency_primary, slope, panel_group), by = "agency_primary") |>
  mutate(
    direction = ifelse(slope < 0, "Declining", "Increasing"),
    # Shorten long agency names for labels
    agency_label = str_remove(
      agency_primary,
      " Police Department$| Police Dept$| Sheriff's Office$| Sheriff's Department$| State Police$| Police$"
    ) |>
      str_trunc(22, ellipsis = "…")
  )

fig4 <- ggplot(plot_agency_data, aes(x = year, y = n_killed, color = direction)) +
  geom_line(linewidth = 0.7, alpha = 0.8) +
  geom_point(size = 1.2) +
  geom_smooth(method = "lm", se = FALSE, linetype = "dashed",
              linewidth = 0.6, alpha = 0.5) +
  scale_color_manual(
    values = c("Declining" = positive_color, "Increasing" = negative_color),
    guide  = "none"
  ) +
  scale_x_continuous(breaks = c(2013, 2019, 2025)) +
  scale_y_continuous(labels = label_number(accuracy = 1)) +
  facet_wrap(~ agency_label, ncol = 4, scales = "free_y") +
  theme_mpv(base_size = 9) +
  theme(
    strip.background = element_rect(fill = "#F5F5F5", color = NA),
    axis.text.x = element_text(angle = 45, hjust = 1, size = 7)
  ) +
  labs(
    title    = "Annual Fatal Police Violence: Top Agencies by Trend Direction",
    subtitle = "Agencies with ≥ 20 killings, 2013–2025; dashed = OLS trend",
    x        = NULL,
    y        = "People killed",
    caption  = "Source: Mapping Police Violence. Federal agencies excluded. Primary agency only for multi-agency incidents."
  )

ggsave(here("figures", "fig4_agency_multiples.png"),
       fig4, width = 6.5, height = 6, dpi = 300)

# ==============================================================================
# 12. Export Summary Tables for Blog Post Inline Stats
# ==============================================================================

message("Exporting summary stats for blog post...")

# Key inline statistics saved for blog cross-verification
blog_stats <- list(
  # National
  n_2025_our_data      = our_count_2025,
  n_2025_mpv_published = mpv_published_2025,
  n_2024               = national_annual$n_killed[national_annual$year == 2024],
  n_2019               = national_annual$n_killed[national_annual$year == 2019],
  n_2013               = national_annual$n_killed[national_annual$year == 2013],
  avg_2013_2024        = round(avg_2013_2024, 0),
  pct_change_2024_2025_ours = round(100 * (our_count_2025 - national_annual$n_killed[national_annual$year == 2024]) /
                                    national_annual$n_killed[national_annual$year == 2024], 1),
  pct_gap_2025         = round(100 * (mpv_published_2025 - our_count_2025) / mpv_published_2025, 1),
  n_off_duty_excluded  = n_off_duty,
  n_2026_partial       = n_2026,
  n_agencies_qualifying = nrow(agency_totals),
  # State
  n_states_improving   = sum(trend_results_state$direction == "Improving"),
  n_states_worsening   = sum(trend_results_state$direction == "Worsening"),
  n_states_sig_either  = sum(trend_results_state$sig, na.rm = TRUE),
  top5_improving_states = trend_results_state |>
    filter(state %in% us_states_only, direction == "Improving") |>
    slice_min(slope, n = 5) |>
    pull(state),
  top5_worsening_states = trend_results_state |>
    filter(state %in% us_states_only, direction == "Worsening") |>
    slice_max(slope, n = 5) |>
    pull(state),
  # Agency
  top10_declining_agencies = top_declining$agency_primary,
  top10_increasing_agencies = top_increasing$agency_primary
)

saveRDS(blog_stats, here("output", "blog_stats.rds"))

# ==============================================================================
# Done
# ==============================================================================

message("\n--- Analysis complete ---")
message(sprintf("National annual counts: output/mpv_annual_national.rds"))
message(sprintf("State annual data:      output/mpv_annual_state.rds"))
message(sprintf("Agency annual data:     output/mpv_annual_agency.rds"))
message(sprintf("State trend results:    output/trend_results_state.rds"))
message(sprintf("Agency trend results:   output/trend_results_agency.rds"))
message(sprintf("Blog stats:             output/blog_stats.rds"))
message(sprintf("Figures:               figures/fig1_national_trend.png"))
message(sprintf("                        figures/fig2_state_trends_map.png"))
message(sprintf("                        figures/fig3_state_multiples.png"))
message(sprintf("                        figures/fig4_agency_multiples.png"))
