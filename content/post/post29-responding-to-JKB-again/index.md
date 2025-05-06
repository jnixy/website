---
title: "Responding to Kang-Brown (again)"
categories: []
date: '2025-05-06T09:00:00Z'
featured: false
featured_image: featured.png
image:
  caption: 
  focal_point: smart
projects: []
subtitle: ""
summary: ""
tags:
- Open science
- Police
- Crime
- Violence
- Neighborhoods
authors: 
- admin
url_pdf: ""
draft: no
---

## Background

In his latest [commentary](https://asc41.org/wp-content/uploads/ASC-Criminologist-2025-05.pdf) on our [research note](https://doi.org/10.1111/1745-9125.12395), Jacob Kang-Brown (JKB) raises six concerns (some old, some new). For what it's worth he also makes clear his point of view regarding the "question of policing":

> From my point of view, the question of policing is not just one about reducing violent crime or gun crime, but is, **rather**, about understanding the harms of policing, i.e. police violence, the criminalization of poverty, and wealth-based pretrial detention (emphasis added).

The social scientific study of policing is broadly interested in both the potential benefits and harms of policing. It's not, nor should it be, an either/or question.

## Our Responses

Ideally, we would've had an opportunity to respond to JKB's latest qualms in the same issue of *The Criminologist*. However, this didn't happen because he submitted his commentary 2 weeks after the deadline for the May/June issue.[^1] So I've responded to each of JKB's latest claims (in italics) below.

[^1]: JKB has had our essay and all our corrected tables since mid-December 2024.

### 1. *Denver PD and Professors Nix et al. use crime categories that differ substantially from FBI crime definitions.*

We were clear that our measure of violent crime was restricted to DPD reported homicides, robberies, and aggravated assaults. This is commonplace in social scientific research focused on crime and policing (e.g., [Ba et al., 2021](https://doi.org/10.1126/science.abd8694); [Braga et al., 2019](https://link.springer.com/article/10.1007/s11292-019-09372-3); [Hinkle et al., 2020](https://doi.org/10.1002/cl2.1089)), and indeed, none of the experts who refereed our work raised any concern over it.[^2] JKB contends we should have adopted a more holistic measure of gun violence that includes crimes like "shots fired" and "brandishing a weapon." This would not be an unreasonable methodological choice. However, it does seem like a stretch to assume that Denver PD was actively "juking the stats" just because the LAPD had apparently been doing so over a decade ago, and that DPD should implement the same reporting practices [LAPD has since implemented](https://www.latimes.com/local/cityhall/la-me-crime-stats-20151015-story.html). That is, it also seems like a stretch to assume *all* "shots fired" and "brandishing a firearm" incidents rise to the level of aggravated assaults, defined by the FBI in the [UCR handbook JKB referenced](https://ucr.fbi.gov/additional-ucr-publications/ucr_handbook.pdf) as

[^2]: Nor any of the participants at interdisciplinary workshops and academic conferences where we presented our work.

> An unlawful attack by one person upon another for the purpose of inflicting severe or aggravated bodily injury. This type of assault usually is accompanied by the use of a weapon or by means likely to produce death or great bodily harm.

To be clear, then, I couldn't find any evidence that FBI instructs local departments to treat "shots fired" and "brandishing a weapon" incidents as aggravated assaults.

### 2. *While Denver PD crime data is continually updated, the authors collected the 2020 data before it had been processed.*

We downloaded crime data during the first quarter of 2021. At one point JKB argued this resulted in unfounded crimes being included in our data for the latter half of 2020 and rendered our findings nonsignificant. Now he says "it does not on its own dramatically impact specific regression models."

### 3. *Soon after 2021, DPD changed protocols for processing and geocoding of crime address data.*

JKB says some of the crimes in our data happened outside Denver. He doesn't clarify the extent of this issue, but apparently it does not affect our results, as he only points out that correcting it "removes noise from the data and improves validity of the analysis."

### 4. *DPD pedestrian and vehicle stop data (akin to stop, question and frisk or traffic stop data) is supposed by the authors to be a measure of "proactive" policing, but close inspection of the data tables indicates responses to 911 calls and burglar alarms that appear to be traditional response to call for service, or reactive policing.*

According to the [National Academies of Sciences, Engineering, and Medicine](https://nap.nationalacademies.org/read/24928/chapter/3#30), there is "no accepted definition of proactive policing among scholars or the public." However:

> In practice, policing strategies range along a continuum between pure proactivity and pure reactivity. The more proactive elements that are present in a given strategy, the more proactive it is. The more reactive elements present in a given strategy, the more reactive it is.

Researchers often employ broad measures of stops and arrests as proxies for police proactivity or "aggressiveness." Part of the motivation for our paper was to improve on existing research by separating traffic and pedestrian stops out from each other and homing in on arrests where officers ostensibly had more discretion (i.e., for drug-related and disorder offenses). Accordingly, we labelled section 2.3.2 of our research note, where we introduce our measures, "Police discretionary behaviors." While we agree it would be great if we could drill down definitively to those stops that were officer-initiated as opposed to citizen-initiated (indeed, we spent many hours trying to figure out a way to do so), we don't believe we were unclear about our approach.

### 5. *...\[A\]n additional sensitivity analysis using a combined, all police stops metric further indicates that there is no statistical relationship between sudden reduction in these measures of proactive policing and violent or property crime.*

JKB argues we should have combined traffic and pedestrian stops into a single measure, but curiously goes on to argue...

> Denver ranges widely from newer, suburban housing tracts where pedestrian stops are very uncommon to a handful of dense neighborhoods where pedestrian stops are the primary form of discretionary police stops. The more suburban areas are still policed, but primarily by vehicle stops.

...Which seems to us to suggest all the more reason to use separate measures. To be clear, the analysis we prepared in 2021 for *The Denver Post* did use a combined measure of stops. Importantly, it was also conducted at the *city level*. As we dug deeper and began preparing a more rigorous analysis for peer review (a process that ultimately took 3 years), we made a number of methodological decisions (and heeded various recommendations from the peer reviewers), including (1) separating traffic and pedestrian stops, and (2) estimating multilevel models (weeks nested within Denver's 78 neighborhoods). In any event, it should come as no surprise that JKB's sensitivity analysis combining pedestrian stops with vehicle stops (which outnumber pedestrian stops 4:1 *and* produced much smaller coefficients in both our original note and the corrigendum) produces a null finding.

### 6. *...\[P\]art of why the authors get the very modest crime reduction results they do for pedestrian stops is because of omitted variable bias. Notably, the authors include a proxy measure of vehicle traffic in neighborhoods (traffic accidents), but they do not include a neighborhood measure of pedestrian activity like residential density.*

JKB correctly points out that we used a proxy for vehicle traffic in neighborhoods -- traffic accidents -- but failed to mention it was measured at Level 1 (i.e., it varied both between and within neighborhoods by week). We also used weekly OpenTable data as an additional proxy for citizen mobility (though as we noted, it was only available at the city level). JKB then adds a measure of population density to our pedestrian stop models, which does not vary across weeks, and says it renders the effect of pedestrian stops nonsignificant.

## In conclusion

Now that we've fixed the merge error and published a corrigendum, it feels a bit like JKB is grasping for straws to discredit our work. Where he was successfully able to ["reverse p-hack"](https://doi.org/10.1371/journal.pbio.3000127) (Chuard et al., 2019) our results, it was only after he made significant changes to our methodological approach (e.g., changing our outcome variable, combining pedestrian and traffic stops into a single measure, adding another control variable). These amount to researcher degrees of freedom, as we pointed out in our essay for *The Criminologist*, and should not be cast as evidence indicating a need for retraction.[^3] That said, the whole point of sharing our data and code was to enable interested readers to scrutinize our work and, potentially, build from it. JKB is certainly entitled to do that, even if we disagree with how he went about it.[^4]

[^3]: See also Loughran & Topalli's [essay on p. 10](https://asc41.org/wp-content/uploads/ASC-Criminologist-2025-05.pdf).

[^4]: Which is to say: on top of [not having his facts straight](https://x.com/jkangbrown/status/1790416534776562157) before going public with his criticisms of our paper, and insinuating we were [ignoring him](https://x.com/jkangbrown/status/1790478436714025429) or [purposely hiding something](https://x.com/jkangbrown/status/1790475204088471636), JKB's tone was very different in his first email to me, where he said our paper was "a very nice example of a rigorous analysis of police data, and I hope it leads to further research in other cities." Given all the concerns he has since expressed publicly, I'm disheartened he wasn't just up front with me from the start. And again, for those who would accuse me of hypocrisy, please click [here](https://jnix.netlify.app/post/post26-our-correction/#fn:1).
