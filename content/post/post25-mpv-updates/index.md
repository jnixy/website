---
authors:
- admin
categories: []
date: "2024-04-09T14:00:00Z"
draft: false
featured: false
image:
  caption: "Image by [David Orban](https://flickr.com/photos/davidorban/) on [Flickr](https://flic.kr/p/76SMMb)"
  focal_point: "smart"
projects: []
subtitle: ""
summary: 
tags:
- Police
- Deadly Force
- Office-involved shootings
title: "A Modified Definition of Police Violence"
url_pdf: ""
---

The other day I got a Google Scholar alert about this [new article](https://injepijournal.biomedcentral.com/articles/10.1186/s40621-024-00496-3) in *Injury Epidemiology*. It's a descriptive study showing that 60% of police killings involve municipal departments, 29% county departments, 8% state departments, 3% federal agencies, and <1% tribal or other departments. It looked interesting (and it was!) so I downloaded the full text, and the following passage in the methods section immediately caught my eye:

> MPV defines fatal police violence as “any incident where a law enforcement officer (off-duty or on-duty) applies, on a civilian, lethal force resulting in the civilian being killed whether it is considered ‘justified’ or ‘unjustified’ by the U.S. Criminal Legal System” (Campaign Zero 2022). MPV thus excludes incidents reported to be caused by speeding or crashing during a police chase, overdose, and in most cases, jumping from a height in a foot chase—i.e., cases in which reviewers determined that police did not directly apply lethal force.

At first I didn't think this was correct, as I've looked at the Mapping Police Violence data pretty closely in the past. Turns out it is correct *now*. MPV apparently modified its inclusion criteria at some point (their [Data & Methodology document](https://mappingpoliceviolence.org/files/MappingPoliceViolence_Methodology.pdf#page=9.09) was last updated on October 3, 2022). 

So here's what happened. Way back in December 2019, I posted [a preprint](https://osf.io/preprints/socarxiv/ajz2q) responding to [this article](https://www.thelancet.com/journals/lancet/article/PIIS0140-67361831130-9/fulltext) in *The Lancet*.[^1] Long story short: my colleague and I argued that 91 incidents in MPV purporting to involve unarmed Black people killed by police should have been re-coded prior to analysis. Broadly, these involved:

* people who had crashed and died while fleeing police, 
* people who were involved in accidental collisions with police vehicles, 
* people who died in correctional facilities, 
* people who were killed by off-duty cops or correctional officers, 
* people who died for reasons that were not attributed to police actions, 
* people who were armed or attempted to gain control of a cop's gun, and 
* people who were holding a toy/replica gun or something that resembled a gun.

Admittedly some of this is subjective![^2] But the point of this post isn't to rehash that debate. Instead, the point is that at one point MPV was including all of the above in their data, but not anymore. I downloaded the data this morning and looked for the 91 incidents we flagged back in 2019. Here's what I found:

| Category                                                    	| As of 12/30/2019 	| As of 4/9/2024 	|
|-------------------------------------------------------------	|:----------------:	|:--------------:	|
| Crashed while fleeing                                       	|        17        	|        0       	|
| Accidental collision with police vehicle                    	|         4        	|        0       	|
| Died in prison                                              	|         4        	|        0       	|
| Murder/manslaughter by off-duty cop or correctional officer 	|        14        	|       13       	|
| Died for reasons not directly attributed to police actions  	|        13        	|        4       	|
| Armed or attempted to grab a police firearm                 	|        13        	|       13       	|
| Toy gun or object that resembled a weapon                   	|        26        	|       26       	|
| **TOTAL**                                                     |      **91**     	|     **56**     	|

Nearly 40% of those 91 incidents no longer appear in the MPV data. All 21 crashes are gone, as are the 4 people who died in prison, and most of the people whose deaths weren't ultimately attributed to police actions. And keep in mind, we only flagged incidents involving unarmed Black people. So while I'm not sure exactly how many deaths were removed from the data after the inclusion criteria were modified, it's inevitably more than shown in the table above.

To be clear: I think MPV's new definition is an improvement, and the updates to the database are a net good. But it does create a bit of a challenge for interpreting the (sometimes conflicting) results of studies that have used MPV over the past 10 years (and those that will use it moving forward). And as always, it concerns me that a lot of the consumers of these and similar datasets don't always seem to recognize or appreciate these little nuances. 

Ian Adams wrote a [Twitter thread](https://twitter.com/ian_t_adams/status/1661726758679224321) about this last May - it's worth a read. 

[^1]: It took some time but the preprint was finally published in [*Police Practice and Research*](https://www.tandfonline.com/doi/full/10.1080/15614263.2021.1878894) on January 31, 2021. 
[^2]: I had people tell me, for example, that a screwdriver shouldn't be considered a weapon, and that Sandra Bland should in fact be treated as a police killing even though her death at the Waller County Jail was [ruled a suicide](https://en.wikipedia.org/wiki/Death_of_Sandra_Bland#Incarceration_and_death).