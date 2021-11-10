---
title: 'Factors associated with police shooting mortality: A focus on race and a plea for more comprehensive data'
authors:
- admin
- John Shjarback
date: "2021-11-10T13:00:00Z"
output: pdf_document
featured: no
image:
  caption: ""
  focal_point: top
  preview_only: no
doi: 10.1371/journal.pone.0259024
projects: []
publication: '*PLOS ONE*'
publication_short: PONE
publication_types: 
- "2"
publishDate: "2021-11-10T13:00:00Z"
slides: ""
summary: "We compile nonfatal police shooting data from four states and find that some racial disparities are larger than previously thought."
tags:
- Police
- Officer-involved shootings
- Gun violence
- Race
- Public health
abstract: "**Objectives**. To quantify nonfatal injurious police shootings of people and examine the factors associated with victim mortality. **Methods**. We gathered victim-level data on fatal and nonfatal injurious police shootings from four states that have such information publicly available: Florida (2009-14), Colorado (2010-19), Texas (2015-19), and California (2016-19). For each state, we examined bivariate associations between mortality and race/ethnicity, gender, age, weapon, and access to trauma care. We also estimated logistic regression models predicting victim mortality in each state. **Results**. Forty-five percent of these police shooting victims (N=1,322) did not die. Black-white disparities were more pronounced in nonfatal injurious police shootings than in fatal police shootings. Overall, Black victims were less likely than white victims to die from their wound(s). Younger victims were less likely to die from their wound(s), as well as those who were unarmed. **Conclusions**. Racial and age disparities in police shootings are likely more pronounced than previous estimates suggest. **Policy Implications**. Other states should strongly consider compiling data like that which is currently being gathered in California. Absent data on nonfatal injurious police shootings – which account for a large share of deadly force incidents – researchers and analysts must be cautious about comparing and/or ranking jurisdictions in terms of their police-involved fatality rates."
url_code: "https://github.com/jnixy/replication-materials/tree/master/nix_shjarback_PONE_2021"
url_dataset: ""
url_pdf: "https://www.crimrxiv.com/pub/xdeitfix/release/3?readingCollection=6c7c25ac"
url_poster: ""
url_project: ""
url_slides: "https://jnix.netlify.app/slides/asc21_pone_paper"
url_source: ""
url_video: ""
---


***************

**BACKGROUND** 

Thanks to [Fatal Encounters](www.fatalencounters.org), [Mapping Police Violence](www.mappingpoliceviolence.org), and [*The Washington Post*](https://www.washingtonpost.com/graphics/investigations/police-shootings-database/), we now have a good idea how often U.S. police officers kill people. For example, WAPO has documented approximately 1,000 fatal shootings by police officers each year since 2015. MPV tracks non-shooting deaths and deaths caused by off-duty officers, and they usually document ~1,100 deaths each year. Fatal Encounters tracks all police-civilian interactions that result in the death of a civilian (including, e.g., a standoff where the suspect shoots him/herself). They find that on average, ~1,800 people have died during police interactions since 2013 (their data go back to 2000 but I'm not sure the totals are as reliable as more recent years). **So police kill (or are involved in the deaths of) 3-5 people each day in the United States.**

What we still **don't** have a good understanding of is **how often police officers** ***use*** **lethal force.**

I've harped on this [before](https://jnix.netlify.app/post/post2-fatality-rates/), and I'm certainly not the first person to do so, but we really should be tracking every time an officer discharges their firearm at another person. With very few [exceptions](https://www.ajc.com/news/crime/in-georgia-agency-police-train-to-shoot-not-kill/IJNVJCHXBRHJHKPFHLEXQ672YI/), police are trained to shoot center mass, and to shoot until the threat (real or perceived) has been neutralized. As James Fyfe [pointed out](https://www.ojp.gov/ncjrs/virtual-library/abstracts/shots-fired-examination-new-york-city-police-firearms-discharges) a long time ago, lethal force is *physical force capable of or likely to kill...it does not always kill.* He went on to argue that *the true frequency of police decisions to employ firearms as a means of deadly force...can best be determined by considering woundings and off-target shots as only fortuitous variations of fatal shootings.*

In other words, police are using lethal force every time they discharge their firearm at a person, regardless of whether that person ultimately dies. 

Fyfe's [analysis](https://doi.org/10.1016/0047-2352(79)90065-5) of NYPD shootings in the early 70s revealed that 44% were fatal. In St. Louis from 2003 to 2012, Klinger and colleagues [found](https://doi.org/10.1111/1745-9133.12174) that 33% of people shot by police died as a result. My colleague [John Shjarback](www.twitter.com/shjarback_ccj) showed that in Texas from 2016-2017, 49% of people who were wounded by police gunfire [ultimately died](https://doi.org/10.1080/0735648X.2018.1547353). And finally, [VICE News](https://news.vice.com/en_us/article/xwvv3a/shot-by-cops) analyzed police shooting data from 47 large jurisdictions and found that 31% resulted in a fatality (and note there was a great deal of [variation](https://jnix.netlify.app/post/post2-fatality-rates/) across jurisdictions in terms of the fatality rate). 

Remember when [Jacob Blake](https://www.nytimes.com/article/jacob-blake-shooting-kenosha.html) was shot in Kenosha last year? Of course you do. There were protests, and they turned violent. Kyle Rittenhouse is currently [on trial](https://www.nytimes.com/2021/11/10/us/kyle-rittenhouse-trial-explained.html) for killing two people and wounding a third. Yet, Jacob Blake's name won't appear in any of the aforementioned databases because he wasn't actually killed. However, he was on the receiving end of police gunfire (i.e., lethal force), and he is now paralyzed from the waist down. 

Researchers (myself included) have used data from Fatal Encounters, Mapping Police Violence, and WAPO to consider a variety of hypotheses about police use of deadly force. And I've reviewed *a lot* more papers yet to be published that do the same. I often wonder if (and how badly) we're misleading ourselves when we do that. I [presented](https://jnix.netlify.app/files/asa19_slides.pdf) a rough outline of my concerns at ASA a few years ago. If we want to improve our understanding of police use of deadly force so that we can seek ways to minimize its occurrence, we need data on police use of deadly force. Data on a nonrandom sample of police use of deadly force (which is what we have now) might be telling us more about the factors associated with mortality in police shootings than about the actual behavior we want to understand. 

**KEY FINDINGS**

John and I just published an [article](https://doi.org/10.1371/journal.pone.0259024) where we demonstrate some of the ways that existing data can mislead. We obtained several years of data on fatal and nonfatal police shootings from four states: [Florida](https://projects.tampabay.com/projects/2017/investigations/florida-police-shootings/), [Colorado](https://ors.colorado.gov/ors-coll-ois), [Texas](https://oagtx.force.com/oisreports/apex/OISReportsPage), and [California](https://openjustice.doj.ca.gov/data). Here are our key findings:

1. Roughly 45% of people wounded by police gunfire in this sample **did not die.** If we assume that survival rate generalizes nationally (and admittedly it may not), it would mean **police shoot and injure another ~800 people each year**, or about 2 people per day (in addition to the 1000 people they fatally shoot each year, per WAPO). 

2. In all four states, Black-white disparities were more pronounced in nonfatal shootings than in fatal shootings. Again, if we assume this holds true nationally, it means we're **underestimating racial disparities** in police use of deadly force. Notice we used the term **disparities** here. There are myriad reasons for those disparities, and attempting to explain the mechanisms driving them were beyond the scope of our paper (not to mention our data). 

3. Conditional on being shot by police, Black people and young people were **less likely** to die. What this suggests is that existing data may be significantly undercounting victims of police lethal force who are young and/or Black (relative to those who are older and/or white), given they are more likely to survive their injuries. 

**IMPLICATIONS**

1. The federal government is still trying to collect better data. The [FBI's new system](https://crime-data-explorer.app.cloud.gov/pages/le/uof) sounds great, as it would address this key concern of ours, but to date only ~6,500 agencies (out of 18,514) are submitting data. I say it "sounds" great because unfortunately, it won't be made public until the agencies submitting data account for at least 60% of all sworn police officers in the US (currently that number is 49%). 

2. In the meantime, more states should follow the lead of Texas and California. Some - like New Jersey, Connecticut, and Maine - already are. Unfortunately, Colorado recently [repealed](https://ors.colorado.gov/ors-coll-ois) its data collection mandate. One of the reasons we've never had comprehensive national data is because participation in the federal government's data collection efforts have always been voluntary and agencies can opt out for whatever reason (e.g., lack of resources). But we now have several examples of success in collecting and compiling data at the state level. If Texas and California can do it, it seems like the other states could. And although it's not ideal (e.g., 50 separate systems that may not align perfectly in terms of what is being measured and how), it'd be a major improvement over the current state of affairs. 

3. Researchers - just beware of the ways that existing data could be misleading. And be transparent about the fact that it is a nonrandom sample of the population we're really trying to understand (i.e., the **use of** lethal force). One of the peer reviewers disagreed with this point and said that not all analyses focused on police use of deadly force necessarily need to acknowledge the "dark figure" we've shed light on here. The reviewer asked us to "substantially revise" that argument. We disagree. To us, it doesn't seem like asking that much for future researchers to **simply acknowledge** the fact that they're working with a nonrandom sample of lethal force incidents. 

Our article is published open access in *PLOS ONE.* It's linked at the top of this page. You can also check out the slides for our upcoming presentation at the *American Society of Criminology* conference in Chicago next week. 
