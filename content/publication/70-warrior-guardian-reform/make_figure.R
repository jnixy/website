library(ggplot2)

reforms <- data.frame(
  item = c(
    "Duty to intervene",
    "Co-responder programs",
    "Ban chokeholds",
    "Prohibit no-knock warrants",
    "Expand civilian oversight",
    "Ban traffic stops\n(non-moving violations)",
    "End qualified immunity"
  ),
  pct = c(84, 76, 41, 27, 16, 8, 6)
)

reforms$item <- factor(reforms$item, levels = rev(reforms$item))

ggplot(reforms, aes(x = pct, y = item)) +
  geom_col(fill = "#2E5C8A", width = 0.65) +
  geom_text(aes(label = paste0(pct, "%")),
            hjust = -0.15, size = 3.5, color = "gray20") +
  scale_x_continuous(limits = c(0, 100),
                     labels = function(x) paste0(x, "%"),
                     expand = expansion(mult = c(0, 0.05))) +
  labs(
    title = "Officer support for police reform proposals",
    subtitle = "% rating each proposal as 'somewhat' or 'extremely' reasonable (n = 217)",
    caption = "Source: Bussey, Nix, McLean & Rojek (forthcoming, Policing & Society).",
    x = NULL, y = NULL
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title    = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10.5, color = "gray40"),
    plot.caption  = element_text(size = 8.5, color = "gray50", hjust = 0),
    panel.grid.major.y = element_blank(),
    panel.grid.minor   = element_blank(),
    panel.grid.major.x = element_line(color = "gray90"),
    axis.text.y = element_text(size = 11),
    plot.margin = margin(10, 20, 10, 10)
  )

ggsave(
  here::here("content/publication/70-warrior-guardian-reform/figure_reform_support.png"),
  width = 7, height = 4.5, dpi = 300
)

message("Figure saved.")
