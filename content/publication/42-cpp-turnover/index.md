---
title: 'Elevated Police Turnover following the Summer of George Floyd Protests: A Synthetic Control Study'
authors:
- Scott Mourtgos
- Ian Adams
- admin
date: "2021-07-06T09:00:00Z"
output: pdf_document
featured: no
image:
  caption: ""
  focal_point: smart
  preview_only: no
doi: 10.1111/1745-9133.12556
projects: []
publication: '*Criminology & Public Policy*'
publication_short: CPP
publication_types: 
- "2"
publishDate: "2021-07-06T09:00:00Z"
slides: ""
summary: "Police resignations - but not retirements or involuntary separations - spiked
  significantly in a large western department following the George Floyd protests."
tags:
- Police
- Legitimacy
- Ferguson Effect
- Organizational justice
- Time series analysis
abstract: "Several of the largest U.S. police departments reported a sharp increase in officer resignations following massive public
protests directed at policing in the summer of 2020. Yet, to date, no study has rigorously assessed the impact of the George
Floyd protests on police resignations. We fill this void using 60 months of employment data from a large police department
in the western US. Bayesian structural time-series modeling shows that voluntary resignations increased by 279% relative
to the synthetic control, and the model predicts that resignations will continue at an elevated level. However, retirements
and involuntary separations were not significantly affected during the study period. A retention crisis may diminish police
departments’ operational capacity to carry out their expected responsibilities. Criminal justice stakeholders must be
prepared to confront workforce decline and increased voluntary turnover. Proactive efforts to improve organizational
justice for sworn personnel can moderate officer perceptions of public hostility."
url_code: ""
url_dataset: ""
url_pdf: "/files/pdfs/cpp_turnover.pdf"
url_poster: ""
url_project: ""
url_slides: ""
url_source: ""
url_video: ""
---

***************

**SUMMARY** 

There's been a lot of talk lately about a staffing crisis in policing following the George Floyd protests last summer. [Minneapolis](https://www.washingtonpost.com/national/minneapolis-police-shortage-violence-floyd/2020/11/12/642f741a-1a1d-11eb-befb-8864259bd2d8_story.html), [Portland](https://www.foxnews.com/us/portland-police-officers-resign-unprecedented-level-defund-police), [San Francisco](https://www.washingtonexaminer.com/news/just-the-beginning-san-francisco-police-officers-leaving-department-in-record-numbers), [Chicago](https://chicago.suntimes.com/2021/1/15/22229584/police-retirements-backlash-chicago-new-york-minneapolis-john-catanzara-fop-michael-lappe), [New York City](https://www.newsday.com/long-island/nypd-retirements-shea-1.50031351), and [Seattle](https://mynorthwest.com/2392075/rantz-seattle-police-lose-nearly-200-officers-mass-exodus-2020/?) all saw increases in police resignations and/or retirements in 2020. According to PERF's recent [survey of 194 agencies](https://www.policeforum.org/workforcesurveyjune2021), resignations increased 18% and retirements increased 45% in 2020-21 (relative to 2019-20). 

[Scott Mourtgos](https://smourtgos.netlify.app/), [Ian Adams](https://ianadamsresearch.com/) and I have a forthcoming article in which we show that resignations in a large western agency[^1] spiked 279% (relative to a synthetic counterfactual) following last summer's protests. However, there were no significant changes in retirements or involuntary separations during our 60-month study period. Here are the yearly counts for each: 

<center>

|Year | Resignations | Retirements | Involuntary Separations |
|-----|:------------:|:-----------:|:-----------------------:|
|2016 | 5            | 21          | 2                       |
|2017 | 9            | 22          | 3                       |
|2018 | 18           | 29          | 4                       |
|2019 | 19           | 21          | 5                       |
|2020 | 37           | 26          | 8                       |

</center>

Probabilistic forecasting models predicted elevated resignation rates would continue in this agency in the months ahead. This is concerning, since it takes approximately one year for newly hired officers to become "road ready." Even if this agency could recruit and hire ~30 officers to replace those who resigned, in the meantime they'd continue to lose ~5 officers per month to new resignations, resulting in a continuing net loss. So if our forecast model is accurate, this agency will need to hire *well* ahead of their authorized size in order to increase staffing.

![fig1](/img/cpp_turnover_forecast.png)

**IMPLICATIONS**

* *Financial concerns*. It costs money to hire, train, and equip new officers. At least [one analysis](https://books.google.com/books/about/Recruitment_Retention_and_Turnover_of_Po.html?id=uKAqWj67tIoC) estimates that the cost of losing an officer ranges from one to five times the salary of that officer.

* *Public safety*. Rapid police officer departures can be detrimental to public safety in the short-term. For example, a [recent study](https://doi.org/10.1080/24751979.2020.1858697) by Eric Piza and Vijay Chillar found that when the Newark Police Department laid off 13% of its officers in 2010, both violent and property crime increased. For what it's worth, in the jurisdiction we studied, violent and property crime increased 22% and 25%, respectively, in 2020. 

* [*Disrupted workforce structure*](https://doi.org/10.1177%2F1098611112456691). On the one hand, if there is rapid turnover in senior- or mid-level ranks, it could require the agency to progress junior officers to higher ranks before they have the experience or skills to perform their new duties. On the other hand, hiring a bunch of new officers to replace those lost to resignations and retirements could result in slower progression (due to a larger cohort of officers competing for a small number of positions), thereby indirectly increasing employee frustration and dissatisfaction. 

**WHAT TO DO?**

* *Publish timely data*. Yes, I'll continue to beat this drum. If all communities had timely data on things like violent crime and police use of force, journalists and citizens could quickly ascertain how their police "stack up" against those in other cities. Absent timely data, it's all too easy to assume that problems in some community getting national media attention (e.g., Minneapolis after the George Floyd murder) are representative of all communities.

* *Fair management*. This goes for police executives as well as mayors, councilmembers, and other "institutional sovereigns." There is a [significant and positive relationship](https://doi.org/10.1111/1745-9125.12251) between perceived organizational fairness and desirable attitudes and behaviors by employees. When officers believe their organizations treat them fairly, they are [less sensitive to outside scrutiny](https://doi.org/10.1016/j.jcrimjus.2016.06.002), remain committed to [doing their jobs](https://doi.org/10.1016/j.jcrimjus.2019.101627), have more [favorable views of the public](https://doi.org/10.1108/13639511311329732), and are less likely to engage in [misconduct](https://doi.org/10.1177%2F0093854810397739). Organizational justice may protect against future staffing crises by reducing [burnout](https://doi.org/10.1108/PIJPSM-06-2019-0094), stress, and [maladaptive behaviors](https://psycnet.apa.org/doi/10.1037/law0000085). So while agencies have little control over how national media coverage of misconduct affects public opinion, leaders *can* [select and train](https://psycnet.apa.org/doi/10.1037/lhb0000273) their front-line supervisors to provide a buffer between community hostility and their sworn personnel. 

* *Resist going along with poorly framed narratives*. There is *plenty* of room for improvement in American policing, and it is necessary to hold police accountable for unlawful actions and even "lawful but awful" actions. But, as one example, I think it's disingenuous (if not [dangerous](https://www.theatlantic.com/ideas/archive/2021/05/what-americans-should-know-about-police-killings-minors/618759/)) to refer to police killings as an ["epidemic"](https://www.aclu.org/report/other-epidemic-fatal-police-shootings-time-covid-19) when we know that each year, just .0002% of [60 million+ police-citizen interactions](https://bjs.ojp.gov/content/pub/pdf/cbpp18st.pdf) result in a citizen being killed. [Elsewhere](https://doi.org/10.1371/journal.pone.0236158), I've griped about the problems with blanket use of the phrase "police violence." The way these issues are framed absolutely matters. Maybe it shouldn't be a surprise that a [recent poll](https://www.skeptic.com/research-center/reports/Research-Report-CUPES-007.pdf) found that most Americans on both sides of the political aisle grossly overestimate how often police officers kill unarmed Black men each year. Or that Black Americans [fear the police even more than they fear crime](https://osf.io/preprints/socarxiv/9hwv7/). 

*****
Click on the **PDF** button at the top of the page to download the full text. Feedback is always welcome!

[^1]: The agency had approximately 600 authorized sworn positions at the time of this study. 
