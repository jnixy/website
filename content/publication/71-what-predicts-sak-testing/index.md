+++
# Paper title
title = "What predicts testing a sexual assault kit? Findings from the Minnesota sexual assault kit initiative project"

# Authors
authors = ["Tara Richards", "Michaela Benson-Goldsmith", "Caralin Branscum", "Brad Campbell", "admin", "Emily Wright"]

# Publication
publication = "*Journal of Criminal Justice*"

# Publication types (2 = Journal article; 3 = preprint; 4 = report; 6 = book chapter)
publication_types = ["2"]

# Date the paper was published.
date = 2026-07-01T10:00:00Z

# Date this page was created.
publishdate = 2026-06-18T11:00:00Z

# Project summary to display on homepage.
summary = ""

# Abstract
abstract = "Prior research has indicated a range of reasons for untested sexual assault kits (SAKs), noting that it is often a multifaceted problem stemming from decades of unclear and/or outdated policies, agency deficiencies, and insufficient resources. There have been few studies to date exploring what factors are related to the decision to submit a SAK for testing. Here, we assess whether sexual assault cases with SAKs that were tested as part of the original investigation are measurably different than sexual assault cases with untested SAKs from the same mid-sized, suburban and rural Midwestern jurisdiction and time period. Using SANE exam forms and police investigative reports from approximately 400 sexual assault cases, we explore whether victim-, perpetrator-, case-, and/or suspect-level factors are related to SAK submission. Results reveal three overarching findings: (1) victims' engagement with the investigation shaped the odds of SAK submission irrespective of other factors; (2) whether the perpetrator was known to the victim mattered for SAK testing in a manner consistent with law enforcement “triaging” practices; (3) case year was impactful, suggesting departmental policies and practices changed over time and that these changes affected testing decisions."

# Tags: can be used for filtering projects.
# Example: `tags = ["machine-learning", "deep-learning"]`
tags = ["sexual assault kits", "policing", "decision-making", "sexual assault kit initiative"]

# Optional external URL for project (replaces project detail page).
external_link = ""

# Slides (optional).
#   Associate this project with Markdown slides.
#   Simply enter your slide deck's filename without extension.
#   E.g. `slides = "example-slides"` references
#   `content/slides/example-slides.md`.
#   Otherwise, set `slides = ""`.
slides = ""

# Links (optional).
url_pdf = ""
url_slides = ""
url_video = ""
url_code = ""

# Custom links (optional).
#   Uncomment line below to enable. For multiple links, use the form `[{...}, {...}, {...}]`.
links = [{name = "DOI", url="https://doi.org/10.1016/j.jcrimjus.2026.102686"}]

# Featured image
# To use, add an image named `featured.jpg/png` to your project's folder.
[image]
  # Caption (optional)
  caption = "Image created with ChatGPT 5.2"

  # Focal point (optional)
  # Options: Smart, Center, TopLeft, Top, TopRight, Left, Right, BottomLeft, Bottom, BottomRight
  focal_point = "Center"
+++

Sexual assault kits (SAKs) — the forensic evidence collected during a medical exam after a sexual assault — are meant to ensure justice for victims. They're also going untested at a rate that might surprise many. A [2021 study](https://doi.org/10.1016/j.jcrimjus.2020.101746) estimated that somewhere between 300,000 and 400,000 SAKs went unsubmitted for DNA testing across the United States between 2014 and 2018. 

The federal [Sexual Assault Kit Initiative (SAKI)](https://bja.ojp.gov/program/saki/overview), launched by the Bureau of Justice Assistance in 2015, has helped address backlogs: as of 2026, SAKI grantees have inventoried more than 205,000 SAKs and enabled testing of more than 105,000. A growing body of research has evaluated these initiatives, documenting the scope and characteristics of untested kits across jurisdictions. But there's a related question that has received far less attention: among cases where a SAK *was* collected, what actually predicts whether it gets submitted for testing in the first place?

That's the question at the center of a new paper I co-authored with Tara Richards, Michaela Benson-Goldsmith, Caralin Branscum, Brad Campbell, and Emily Wright, just published in the *Journal of Criminal Justice*. We analyzed approximately 400 sexual assault cases from a midsized, suburban and rural Minnesota county to understand what separates cases where the SAK was tested from cases where it wasn't. The findings are instructive — and in some places sobering.

**The Study**

Our data come from the Minnesota Sexual Assault Kit Initiative (MN SAKI) project, centered on the Anoka County Sheriff's Office. Minnesota's state legislature mandated a statewide SAK inventory in 2015, which identified more than 3,400 previously untested SAKs across the state — 503 of them at Anoka County alone. Our research team joined the MN SAKI project in 2020 to provide external evaluation capacity.

The sample includes 408 criminal sexual conduct cases from 2008 to 2015: 165 that had a SAK submitted and tested during the original investigation, and 243 whose SAKs went untested. The 40% submission rate in our sample sits roughly in line with prior research from some western U.S. jurisdictions, though submission rates vary enormously across studies — one recent sample had a 90% rate — which itself tells you how much organizational context shapes these numbers.

What distinguishes our study from every prior study on this question is the data source. Previous research on SAK submission has relied exclusively on Sexual Assault Nurse Examiner (SANE) records — the documentation from the forensic medical exam. We had access to SANE forms *and* police investigative reports, which meant we could examine variables like whether the victim expressed a desire to pursue an investigation, whether a suspect had been identified, whether there were witnesses, and details of the investigative approach. Those are factors prior studies simply couldn't examine, but that are likely central to how investigators make submission decisions. We estimated logistic regression models — with bootstrapping to support stable estimates given some small cell sizes — adding victim, perpetrator, case, and suspect characteristics in sequence across four models.

**Finding 1 — It Came Down to Whether Victims Stayed Engaged**

The clearest and most consistent finding across all four models: victim engagement with the investigation was the dominant predictor of whether a SAK was tested.

In the group of cases where SAKs were submitted, 85.4% of victims had expressed a desire to pursue an investigation. In the untested group, that figure was 55.7%. Victims who affirmatively said they didn't want an investigation had roughly 80% lower odds of having their SAK submitted (OR = 0.209, 95% CI [0.07, 0.61]). Victims who initially cooperated but later changed their minds had even lower odds — about 95% lower (OR = 0.050, 95% CI [0.01, 0.20]). That is the single strongest effect in the entire study.

There's also a counterintuitive finding worth pausing on. Victims who reported to police on the same day as the assault were actually *less* likely to have their SAK tested, not more (OR = 0.128, 95% CI [0.04, 0.37]). This seems backwards at first — shouldn't faster reporting help? The explanation, we think, is about what same-day reporting gives investigators access to. When a victim reports immediately, witnesses are still around, suspects are easier to locate, and memories are fresh. Officers can pursue interviews and other leads. In cases reported days or weeks later — when those avenues have closed — forensic DNA may be the most viable path forward, making submission more likely. (Note that this variable measures when the victim reported to police, not how long after the assault the SANE exam occurred; prior research consistently finds that time-to-exam does not predict SAK testing.)

What the data don't — and can't — tell us is why victims disengaged. Some genuinely chose not to pursue charges. But prior research, particularly work by [Lovell and colleagues](https://doi.org/10.1007/s12103-020-09573-x), documents a "bureaucratic burden" placed on victims of sexual assault: a system that requires continuous engagement to advance a case, where institutional processes are frequently retraumatizing, and where disengagement is sometimes the product of a hostile system rather than a free choice. Investigators' case notes recording that a victim "changed her mind" or "stopped returning calls" may reflect the investigators' framing more than the victim's actual preferences. Disentangling autonomous choice from system-induced attrition is difficult with case file data, and the current study is no exception.

**Finding 2 — Who the Perpetrator Was (and Wasn't) Mattered**

Cases involving an unknown, single perpetrator were roughly four times more likely to have the SAK submitted compared to cases with a known, single perpetrator (OR = 4.359, 95% CI [1.61, 11.82]). This is consistent with what researchers call "triage" logic — the practice, well documented in prior qualitative research, of investigators submitting SAKs primarily when they believe DNA evidence will help identify an unknown suspect. When the perpetrator is already known to the victim, the case typically turns on consent rather than identity, and DNA evidence may seem less relevant to investigators.

One additional finding here is more nuanced: cases involving *known*, multiple perpetrators were also more likely to have the SAK submitted (OR = 4.790, 95% CI [1.19, 19.20]). In group or gang assault cases, the question isn't just "was there a sexual assault?" but "who specifically was involved?" DNA evidence can help establish which individuals were present — directly relevant to arrest and charging decisions, including distinguishing principal offenders from accessories. A prior study by [Shaw and Campbell (2013)](https://doi.org/10.1177/0886260513504496) found the opposite pattern among adolescent kits, though they didn't distinguish between known and unknown multiple-perpetrator cases, which may explain the discrepancy.

**Finding 3 — When the Case Happened Mattered Enormously**

Perhaps the most striking finding in the study is how much the calendar year of the case predicted submission — more than most individual-level characteristics we measured.

Compared to cases from 2015, cases from every prior year in our sample were significantly less likely to have been tested. The gradient was steep. Cases from 2014 had about one-quarter the odds of 2015 cases (OR = 0.261). Cases from 2011 had about one-twelfth the odds (OR = 0.083). And cases from 2010 had roughly one-fortieth the odds (OR = 0.025). 

What changed? Not the characteristics of individual victims or perpetrators — those were controlled for in the model. What changed was the organizational environment. Minnesota's 2015 legislative mandate to inventory untested SAKs statewide was the formal trigger, but the pattern in our data suggests that Anoka County's practices were already shifting toward a "test-all" approach in the years leading up to that mandate. Departmental culture, resource allocation, and prevailing policies all evolved over time — and those changes shaped which cases received forensic attention more powerfully than any individual-level characteristic we examined.

**What Didn't Predict Testing (and Why That Matters)**

The factors that *didn't* predict SAK submission are as informative as those that did.

Victim race, victim age, injury status, mental health status or disability, whether the officer recorded skepticism about the victim's credibility — none of these were significantly related to SAK submission in our models. The same holds on the suspect side: suspect race, suspect age, and whether the suspect was interviewed were all non-significant. Assault location and the presence of witnesses didn't matter either.

The null finding on officer-recorded credibility questioning is worth flagging. Research from Detroit and Houston has found that informal credibility assessments — shaped by stereotypes about victim behavior, lifestyle, and demographics — played a substantial role in which cases moved forward. We didn't replicate that pattern here. There are at least two ways to interpret this. One is that the Anoka County context is genuinely different from large, diverse urban jurisdictions. The other is that case file documentation of officer skepticism is an imperfect proxy for the attitudes actually shaping decisions — officers may hold credibility concerns that never make it into the written record. Both explanations are plausible, and the discrepancy between our findings and prior research in urban settings is worth continued attention as this literature grows.

**Summary of Key Predictors**

| Predictor | Direction | Approx. Odds Ratio |
|-----------|-----------|---------------------|
| Victim reported same day | ↓ Less likely to be tested | 0.14 |
| Victim did not want investigation | ↓ Less likely | 0.20 |
| Victim changed mind about investigation | ↓ Less likely | 0.06 |
| Unknown, single perpetrator | ↑ More likely | 4.36 |
| Known, multiple perpetrators | ↑ More likely | 4.79 |
| 2010 (vs. 2015) | ↓ Less likely | 0.03 |
| 2011 (vs. 2015) | ↓ Less likely | 0.08 |
| 2012–2014 (vs. 2015) | ↓ Less likely | 0.18–0.26 |

*ORs from Model 3 (victim + perpetrator + case characteristics, n = 354). Full results in Table 3 of the published article.*

**What This Means**

The dominant policy response to untested SAK backlogs has been the push for "test-all" mandates — policies requiring that all collected SAKs be submitted for forensic analysis regardless of investigators' assessments about evidentiary value. That shift is well underway nationally, and it's the direction our findings support.

But the findings also clarify where "test-all" policies will primarily make a difference: cases where victims disengaged from the investigation. Those are precisely the cases most likely to have gone untested under the old discretionary regime. Mandating testing in those cases — regardless of victim participation status — represents a meaningful expansion of forensic investigation. It also raises a genuine tension. Victim-centered and trauma-informed frameworks emphasize respecting victims' autonomy throughout the justice process. Submitting a SAK over a victim's expressed objection is a different policy choice than submitting one when a victim simply stopped returning calls. Policies should account for that distinction, even as the general principle of universal testing gains traction.

The more fundamental implication is that SAK submission is not primarily a case-level phenomenon — it's an organizational one. The clearest signal in our data is the year effect, which tracks changes in departmental culture and policy rather than anything about individual victims or perpetrators. That means the real levers for change sit at the agency and system level: policies, training, resources, and the broader institutional environment in which investigators operate. Reducing the bureaucratic burden on victims — through trauma-informed response protocols, embedded victim advocates, and anonymous kit storage options for victims who don't wish to report at the time of the exam — may matter as much as any mandate about what happens to the kit itself.

*A note on limitations:* This study comes from a single jurisdiction — a predominantly White, midsized, suburban and rural Minnesota county — which differs in important ways from the large, diverse urban settings where most prior SAK research has been conducted. Our findings may not generalize beyond similar contexts, and continued replication across different jurisdictions is essential. The analysis is also constrained to 2008–2015, predating the formalized "test-all" shift in Anoka County. And because male victims and female perpetrators appeared in very small numbers in the case files, we excluded those cases — a limitation shared by most research in this area, and one that future work with larger samples should address.
