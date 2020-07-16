---
authors:
- admin
categories: []
date: "2019-07-30T13:25:00Z"
draft: false
featured: false
image:
  caption: ""
  focal_point: "top"
projects: []
subtitle: ""
summary: My thoughts after reading.
tags:
- Officer-involved shootings
- Police
- Race
title: That new study in PNAS on fatal officer-involved shootings
url_code: "https://github.com/jnixy/replication-materials/tree/master/nix_blog_3"
---
A new study published in PNAS, titled ["Officer characteristics and racial disparities in fatal officer-involved shootings"](https://www.pnas.org/content/early/2019/07/16/1903856116) is getting lots of [attention](https://pnas.altmetric.com/details/63894008/news) (34 news articles and tweeted by 1,808 users with an upper bound of 9.8 million followers as of 7/30/2019). It concludes, among other things, that "White officers are not more likely to shoot minoritiy civilians than non-White officers," and "Increasing diversity among officers by itself is unlikely to reduce racial disparity in police shootings."

[Others](https://twitter.com/DrPhilGoff/status/1155916041924431872) have been [critical](https://twitter.com/jonmummolo/status/1153686295845244929) of the study, for good reason.

I commend the authors for being up front about a key limitation of their work: "Our analyses speak to racial disparities in the subset of shootings that result in fatalities, and not officers' decisions to use lethal force more generally." But unfortunately, this gets lost in [media coverage](https://abcnews.go.com/Health/fatal-police-shootings-race-officer-predictive-civilians-race/story?id=64563567&cid=clicksource_4380645_null_headlines_hed) and [tweets](https://twitter.com/PoliceOne/status/1155914391973441536).

I've [posted](https://jnix.netlify.com/post/post2-fatality-rates/) about this before. Fatal OIS are not a random sample of all OIS, so statistical analyses of them may serve to mislead us rather than shed light on the truth. Take a look at Table 2 on page 3 of their study:

![pnas_table2](/img/pnas_table2.png)

The million dollar question here is: how often did each "variable" occur in 2015 when officers __did not use deadly force__? As but one example, how often did police officers encounter suicidal civilians? In a _small subset_ of these incidents, officers fatally shot the suicidal citizen. That's what is being analyzed in Table 2 for evidence of racial disparity. Not included in Table 2 are numerous incidents wherein the outcome was something other than a fatal OIS (e.g., nonfatal OIS, less lethal force, no force). Without knowing the racial breakdown of these counterfactual incidents, it isn't possible to conclude anything about the "likelihood" of officers shooting minorities.

Next month, at the [ASA meeting](https://convention2.allacademic.com/one/asa/asa19/index.php?cmd=Online+Program+View+Session&selected_session_id=1479837&PHPSESSID=2b88b5bc2glse47gdg2iriajh5) in NYC, Geoff Alpert and I will be discussing the benefits and drawbacks of analyzing crowdsourced OIS data. Chief among the drawbacks is that most track only fatal OIS, and the racial breakdown of fatal OIS often differs substantially from the racial breakdown of __all__ OIS. Here's a table I made with the [VICE data](https://news.vice.com/en_us/article/a3jjpa/nonfatal-police-shootings-data) I mentioned in my last post.

![asa_comparison_table](/img/asa_comparison_table.png)

Among 21 jurisdictions with near complete data (< 5% missing) on the race of citizens shot by police from 2010-16, you can see that as you move from examining just fatalities to examining all OIS, %white decreases while %black increases. In some cities, the differences are more pronounced than others. Take Nashville, for example, where there were 39 OIS (only 11 of which were fatal):

![asa_nmpd](/img/asa_nmpd.png)

In this case, %white and %black basically flip from fatal OIS to all OIS. Perhaps the differences would be nonsignificant in a national database, but that remains unknown since no national database includes nonfatal OIS. 

__We need to know about every time an officer shoots at a person, regardless of whether the person is killed.__ We also need to know about the universe of incidents wherein it might have been reasonable for officers to use deadly force, but they [refrained from it](https://journals.sagepub.com/doi/pdf/10.1177/0011128718756038). But as others have [pointed out](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3336338), police administrative records are themselves biased if officers racially discriminate when choosing whom to investigate (the implication is we also need to know who they _don't_ stop). There are no easy answers here. But for now, I see no reason why we can't track nonfatal in addition to fatal OIS.

*****************************

<div class="alert alert-info" role="info">
  <p style="text-align:center"> Click the CODE button at the top of this page to replicate these figures using Stata. </p>
</div>