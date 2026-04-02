---
title: "A Year Over Year Decline Isn't a Trend, but Hopefully It's a Start?"
authors:
- admin
date: "2026-04-02"
categories:
- policing
- data
- deadly force
tags:
- policing
- criminology
- data
featured: true
draft: false
image:
  caption: ""
  focal_point: "smart"
links: ""
url_code: "01_mpv_trends.R"
summary: "Mapping Police Violence reports a 5% decline in police killings for 2025."
---

> In 2025, fatal police violence declined for the first time in six years—clear evidence that sustained, long-term activism works. 

So begins a [recent statement](https://campaignzero.org/research/mapping-police-violence-for-the-first-time-in-six-years-police-violence-declined-in-2025/) by Campaign Zero, following its 2025 Year End Report. I came across it this morning after seeing a story in [Stateline](https://stateline.org/2026/04/01/fatal-police-violence-may-have-declined-for-the-first-time-in-years/). The [Mapping Police Violence](https://mappingpoliceviolence.us) data are among the most comprehensive we have—compiled from news reports and official records, updated continuously, and including deaths that federal reporting systems routinely miss. But a single year of modestly lower numbers does not establish a trend, and I wouldn't be so quick to chalk up the decline to "sustained, long-term activism." It could very well be statistical noise.

## The Number in Context

{{< figure src="fig1_national_trend.png" caption="Source: Mapping Police Violence, downloaded April 2026. The 2025 value reflects my extract (1,173); MPV's published figure is 1,314. See text for explanation of the gap." >}}

A word first on the numbers themselves. Campaign Zero's report says police killed 1,314 people in 2025. The figure above draws on the underlying victim-level [MPV dataset](https://mappingpoliceviolence.us/s/MPVDatasetDownload.xlsx), which I downloaded this morning (April 2, 2026). There were 1,201 victims listed for 2025. I excluded a small number of killings by off-duty police officers, bringing my analytic *N* down to 1,173. I'm not sure what explains the discrepancy. But with that caveat noted: the general direction holds. Killings declined by ~5% in 2025 compared to 2024, in both MPV's published figures and the data I downloaded this morning.

The trouble with celebrating this is the baseline. Police killed 1,028 people in 2013—the earliest year in this dataset. From 2020 onward, the annual count never came back down to that level. The 2025 figure, even at MPV's 1,314, is still higher than every year from 2013 through 2019. The 1,109-person average from 2013 through 2024 tells you where we've been. The post-2019 plateau is the story; a modest dip from a record high doesn't reverse it.

And this isn't the first time a one-year decline generated cautious optimism that turned out to be premature. Killings dropped in 2019 from 2018's levels. Then came 2020.

## Why Single-Year Changes Are Hard to Trust

There are structural reasons to be cautious about any single year's numbers.

There's no universal reporting mandate in the United States. Police departments are not required to report killings to any central authority in a standardized way. The FBI's supplemental homicide data and the Bureau of Justice Statistics' Arrest-Related Deaths program have both had well-documented gaps. MPV fills much of that void by going directly to news records and public documents, but that methodology comes with its own lag structure—incidents that aren't covered by local media or that don't generate public records requests may take months or years to surface. For more on this, see [*Deadly Force: Police Shootings in Urban America*](https://press.princeton.edu/books/hardcover/9780691260785/deadly-force) by Tom Clark and colleagues. 

What this means practically: year-over-year changes in the most recent year are systematically less reliable than changes for years further in the past. The 2025 number may continue to grow as more incidents are captured. Whether it grows enough to change the directional story is unknowable right now.

## Where Things Are Getting Worse—and Better

The national headline conceals enormous variation at the state and local level. Looking at 2013–2025 trends, states with *declining* rates of police killings per 100,000 residents are actually the minority: 15 states show negative slopes over this period, versus 36 with rising rates. Of the states with statistically meaningful trends, the picture tilts toward worsening.

{{< figure src="fig2_state_trends_map.png" caption="Rate trends by state, 2013–2025. Most trends are modest in magnitude; colors show direction. Source: Mapping Police Violence; ACS population estimates." >}}

{{< figure src="fig3_state_multiples.png" caption="Annual rates per 100,000 residents for the states with the steepest declining and rising trends. Dashed lines show OLS fits. Source: Mapping Police Violence; ACS population estimates." >}}

A few states show consistent rate declines—Maryland, California, Massachusetts, and New Jersey among them. The most common pattern for these states involves a combination of factors: dense urban areas where police reform advocacy has been most organized; state-level legislative action on use-of-force standards; and, in some cases, sustained accountability pressure following high-profile killings.

The states moving in the other direction include Alaska, North Dakota, New Mexico, Idaho, and Indiana. These states tend to be either mostly rural states where a small absolute number of killings translates into large rate changes, or states where law enforcement growth has outpaced population growth. New Mexico and Alaska in particular have faced sustained scrutiny over police violence and have struggled to implement durable reforms.

## The Agency-Level Story

{{< figure src="fig4_agency_multiples.png" caption="Annual killings for the 10 agencies with the most consistent declines and the 10 with the most consistent increases, 2013–2025. Agencies must have recorded 20 or more killings across the period to qualify. Source: Mapping Police Violence." >}}

Among the 117 law enforcement agencies in the data with at least 20 killings over the 2013–2025 period, the trend lines run in both directions.

The agencies showing the steepest consistent *declines* include the Chicago Police Department, the Los Angeles County Sheriff's Office, the Los Angeles Police Department, Miami-Dade Police, and the Oklahoma City Police Department. Several of these agencies have been operating under federal consent decrees or intensive reform agreements. Chicago's 2017 consent decree with the Illinois Attorney General came after a Justice Department investigation documenting systematic civil rights violations; LAPD has faced decades of federal oversight. Whether the declines reflect genuine reform or reduced policing intensity—the so-called "depolicing" debate—remains contested in the literature. What's clear is that these agencies are killing fewer people than they were a decade ago.

The agencies showing consistent *increases* include the San Bernardino County Sheriff's Office, the Pennsylvania State Police, the San Antonio Police Department, Albuquerque Police, and the Arkansas and New York State Police. Albuquerque's trajectory is particularly notable given that it has also been under a DOJ consent decree since 2014—a reminder that reform agreements don't automatically translate into declining violence, especially in the short term.

Some of the increase in state police figures may reflect their expanded role in responding to rural incidents that would previously have gone unrecorded or been attributed to local departments. That doesn't make the numbers less real; it may partly explain their trajectory.

## What the Data Can and Can't Tell Us

I want to be careful here about what conclusions the data support.

We can say: national counts appear to have declined modestly in 2025 compared to a record-high 2024, though that number remains provisional. We can say: most states show rising rates over the 2013–2025 period, with the Northeast and mid-Atlantic being partial exceptions. We can say: specific large agencies—Chicago, LA—are killing fewer people than they were, and this coincides with reform agreements and political pressure.

We can't say: the problem is getting better. One year below a record high is not a trend. The post-2019 elevation in killings—roughly 130 more people killed per year compared to the 2013–2018 average—hasn't reversed. We can't confidently attribute the agency-level declines to any specific policy without a more rigorous research design.

The MPV team does genuinely important work, and their data represent the best available evidence on a problem the federal government still won't systematically track. The 2025 figure warrants attention. But the way to honor their work is to read it carefully—which means reading past the headline, into the variation, and into the uncertainty.

---

*Analysis draws on the Mapping Police Violence victim-level dataset downloaded April 2026. Off-duty killings excluded (n = 369). For incidents with multiple agencies listed, the first-listed agency is used. An additional 267 partial-year 2026 records are excluded from trend analysis. Code and data available at the top of the page.*
