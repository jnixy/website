library(ggplot2)

transparency <- data.frame(
  score = 0:6,
  n     = c(87, 45, 63, 109, 163, 175, 88)
)
transparency$pct <- round(100 * transparency$n / sum(transparency$n), 1)

ggplot(transparency, aes(x = factor(score), y = n)) +
  geom_col(fill = "#2E5C8A", width = 0.65) +
  geom_text(aes(label = paste0(n, " (", pct, "%)")),
            vjust = -0.5, size = 3.3, color = "gray20") +
  scale_y_continuous(limits = c(0, 190), expand = expansion(mult = c(0, 0.05))) +
  labs(
    title = "How transparent are agency hiring pages?",
    subtitle = "Number of agencies scoring each Transparency Index value, 0-6 (n = 730)",
    caption = "Source: Hashimi, Cotton, Huff, Kearns & Nix (forthcoming, Policing: An International Journal).",
    x = "Transparency Index (0 = least, 6 = most)", y = NULL
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title    = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10.5, color = "gray40"),
    plot.caption  = element_text(size = 8.5, color = "gray50", hjust = 0),
    panel.grid.major.x = element_blank(),
    panel.grid.minor    = element_blank(),
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank(),
    plot.margin = margin(10, 15, 10, 10)
  )

ggsave(
  here::here("content/publication/72-hiring-and-screening/figure_2.png"),
  width = 7, height = 4.5, dpi = 300
)

message("Figure 2 saved.")
