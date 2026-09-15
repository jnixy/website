library(ggplot2)

coefs <- data.frame(
  predictor = c(
    "Region: West",
    "Sworn: 500+ officers",
    "Sworn: 100-499 officers",
    "Region: South",
    "Region: Midwest",
    "Type: Municipal police"
  ),
  b   = c(1.59, 1.33, 1.13, 1.06, 0.76, 0.62),
  se  = c(0.20, 0.16, 0.15, 0.19, 0.22, 0.12),
  sig = c("***", "***", "***", "***", "**", "***")
)

coefs$ci_lo <- coefs$b - 1.96 * coefs$se
coefs$ci_hi <- coefs$b + 1.96 * coefs$se
coefs$predictor <- factor(coefs$predictor, levels = rev(coefs$predictor))

ggplot(coefs, aes(x = b, y = predictor)) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "gray50") +
  geom_errorbarh(aes(xmin = ci_lo, xmax = ci_hi), height = 0.15,
                 color = "#2E5C8A", linewidth = 0.6) +
  geom_point(color = "#2E5C8A", size = 3.5) +
  geom_text(aes(x = ci_hi, label = paste0("b = ", sprintf("%.2f", b), " ", sig)),
            hjust = -0.12, size = 3.4, color = "gray20") +
  scale_x_continuous(limits = c(-0.2, 2.5), expand = expansion(mult = c(0, 0.05))) +
  labs(
    title = "Which agencies post more hiring information online?",
    subtitle = "OLS coefficients predicting the Transparency Index, with 95% CIs (n = 730)",
    caption = paste(
      "Reference groups: Sheriff's Office, agencies with <100 sworn officers, Northeast.",
      "** p<.01, *** p<.001.",
      "Source: Hashimi, Cotton, Huff, Kearns & Nix (forthcoming, Policing: An International Journal).",
      sep = "\n"
    ),
    x = "Unstandardized OLS coefficient", y = NULL
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title    = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10.5, color = "gray40"),
    plot.caption  = element_text(size = 8, color = "gray50", hjust = 0),
    panel.grid.major.y = element_blank(),
    panel.grid.minor    = element_blank(),
    panel.grid.major.x = element_line(color = "gray90"),
    axis.text.y = element_text(size = 11),
    plot.margin = margin(10, 20, 10, 10)
  )

ggsave(
  here::here("content/publication/72-hiring-and-screening/figure_3.png"),
  width = 8, height = 4.5, dpi = 300
)

message("Figure 3 saved.")
