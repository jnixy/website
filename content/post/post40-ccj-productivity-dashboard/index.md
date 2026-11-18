---
title: "Introducing the CCJ Productivity Dashboard"
subtitle: ""
authors:
- admin
date: "2026-11-17"
categories:
- data
- bibliometrics
- doctoral programs
- criminology
- criminal justice
- publishing
tags:
- criminology
- data
featured: true
draft: false
image:
  caption: "The dashboard's program-level coauthorship network, 2020–2024"
  focal_point: "smart"
links:
- name: Data and Code
  url: "https://github.com/jnixy/ccj-phd-productivity-2020-2024"
  icon_pack: fab
  icon: github
summary: ""
---

## 2026 has been many things, including the "Year of the Dashboard"

I figure one more couldn't hurt. This one shows where the 44 member programs of the [ADPCCJ](https://adpccj.com/) published, how often they published, and with whom they published from 2020 to 2024. It assigns "authorship credit" to faculty members based on order of authorship, number of authors, and "prestige" of the journal (following the methodology used by [Kleck & Mims (2017)](https://doi.org/10.1080/10511253.2016.1146008)). You can also see how the resulting "rankings" have shifted over time and how sensitive they are to how "prestige" is defined. Finally, you can view a program-level social network - i.e., how connected programs are as measured by co-authorships. If you click on a program node in the network, it'll show you that program's faculty-level network.

The dashboard is linked [here](https://jnix.netlify.app/ccj-productivity) and at the menu at the top of the page, if you want to cut to the chase. If you want to nerd out on all the nitty gritty details, you can read our preprint [here](https://doi.org/10.21428/cb6ab371.4781db71). As always, constructive feedback welcome if you have it. 

But for some reason I feel the need to explain my motives here, so...

## Why I did this

Mostly because I'm on sabbatical this academic year and I have more time on my hands to pursue these random ideas. But also: before I left, my department was having lots of discussions about how to improve our curriculum, get more graduate students to choose UNO, and otherwise continue to improve our standing in the discipline. We know we've been doing some really great things the past few years. But how do we stack up to other PhD programs in crim/CJ? To answer that, we needed some actual data rather than vibes or anecdotes. 

So I knew about the last few studies by Kleck and colleagues on publishing productivity in crim/CJ doctoral programs. The last one's "rankings" covered 2010-2014, a period when I was still in grad school. A lot has changed since then, obviously. I've occasionally thought about replicating it with newer data, but could never find the time. But like I said, I'm on sabbatical at the moment. And so one day earlier this semester, I thought: *I wonder if Claude could do the heavy lifting here if I give it the prior studies and tell it what I want.* 

Turns out, the answer was mostly yes. Probably not surprising to readers who've spent any time using generative AI to aid with their research. I'd estimate Claude got me 80% of the way there, at which point a student and I had to clock in and do quite a bit of manual reviewing and cleaning. We also contacted chairs and/or colleagues at the other 43 member programs of the ADPCCJ and asked them to take a look at the data we'd compiled for them and let us know if there were any mistakes. Most programs caught at least a few minor mistakes. One or two caught oversights I would've been embarrassed about. But I've come to understand that mistakes are inevitable. Open science practices like this help us identify and correct them; otherwise, there's a good chance we'd never discover them. The latter is way scarier to me.[^mistakes]

## To be clear...

Publishing peer-reviewed journal articles is but one little slice of what most academics do (and mileage varies, of course). Thus it's not the *only* thing we should consider when we compare programs. However, it is one of the most publicly visible things we do (so to speak).[^oa] We teach, we sit on committees, we review other researchers' manuscripts, we apply for grants and spend years working on them. We also publish our research findings in other venues (books, technical reports, op-eds, etc.). The last thing I'm trying to do with this project is minimize all those other important ways that faculty can make an impact.

## Good faith replication

One of our goals was to replicate earlier waves to maintain comparability. That meant, among other things: (1) consistently counting all faculty, including those holding administrative appointments who aren't really expected to publish, and (2) using the same "prestige" ratings as before (though supplementing with newer alternatives). On #2, I recognize faculty members sometimes publish in journals in other disciplines with high impact factors. To be sure, comparing impact factors across fields is a fraught exercise, which, as I understand it, is part of the reason the new journal citation indicator (JCI) metric was developed. In any event: take these credit scores with a grain of salt. Perhaps in future releases we can improve on the scoring system.

[^mistakes]: There may still be some mistakes, especially with regard to articles not indexed by OpenAlex. At the bottom of the dashboard there's a form you can submit if you do spot an error. I'll review them, make revisions, and push out updates as needed.

[^oa]: Unfortunately it remains true in 2026 that most of our published articles sit behind expensive paywalls, where most of the public will never see them. For more on this, see the Discussion section of the preprint.
