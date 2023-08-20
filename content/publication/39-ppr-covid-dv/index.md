+++
# Paper title
title = "The immediate and long-term effects of COVID-19 stay-at-home orders on domestic violence calls for service across six U.S. jurisdictions"

# Authors
authors = ["admin", "Tara Richards"]

# Publication
publication = "*Police Practice & Research*, 22(4), 1443-1451"

# Publication types (2 = Journal article; 3 = preprint; 4 = report; 6 = book chapter)
publication_types = ["2"]

# Date this page was created.
date = 2021-01-25T20:00:00Z

# Project summary to display on homepage.
summary = "In 5 of 6 jurisdictions, domestic violence calls for police service spiked during stay-at-home orders"

# Abstract
abstract = "We assessed immediate and long-term trends in calls for police service regarding domestic violence following COVID-19 stay-at-home orders. Using open data from the *Police Data Initiative*, we performed interrupted time-series analyses of weekly calls for service for domestic violence in New Orleans (LA), Cincinnati (OH), Seattle (WA), Salt Lake City (UT), Montgomery County (MD), and Phoenix (AZ). Results indicate that five of the six jurisdictions experienced an immediate, significant spike in domestic violence calls for service (Cincinnati being the lone exception). As stay-at-home orders were lifted throughout the remainder of 2020, domestic violence calls for service declined in every jurisdiction but Salt Lake City. These results illustrate (1) the importance of studying the *localized* effects of COVID-19 on criminal justice issues, (2) the need for more agencies to publish open data in a timely fashion, and (3) the caution researchers and the public must use when working with calls for service data, which are not uniform across agencies and require careful cleaning prior to analysis."

# Tags: can be used for filtering projects.
# Example: `tags = ["machine-learning", "deep-learning"]`
tags = ["Police", "Time series analysis", "Evidence-based policing", "COVID-19", "Cooperation"]

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
url_project = ""

# Custom links (optional).
#   Uncomment line below to enable. For multiple links, use the form `[{...}, {...}, {...}]`.
links = [{name = "Postprint", url="https://assets.pubpub.org/oibiaw6d/71636036997434.pdf"}, {name = "DOI", url="https://doi.org/10.1080/15614263.2021.1883018"}, {name = "Replication Materials", url="https://github.com/jnixy/replication-materials/tree/master/nix_richards_PPR_InPress"}]

# Featured image
# To use, add an image named `featured.jpg/png` to your project's folder. 
[image]
  # Caption (optional)
  caption = "Image by [Sharon McCutcheon](https://unsplash.com/@sharonmccutcheon) from [Unsplash](https://unsplash.com/photos/gxkWSW6K15Y)"
  
  # Focal point (optional)
  # Options: Smart, Center, TopLeft, Top, TopRight, Left, Right, BottomLeft, Bottom, BottomRight
  focal_point = "Smart"
+++

***************

**Summary**

In a new article with my colleague [Tara Richards](https://www.unomaha.edu/college-of-public-affairs-and-community-service/criminology-and-criminal-justice/about-us/tara-richards.php), we examine trends in domestic violence (DV) calls for police service in 6 US jurisdictions from 2018 to 2020:

* New Orleans, LA
* Cincinnati, OH
* Seattle, WA
* Salt Lake City, UT
* Montgomery County, MD
* Phoenix, AZ

We were interested in:

1. Whether DV calls for service spiked during COVID-19 stay-at-home orders[^1], and
2. How DV calls for service trended throughout the remainder of 2020, as stay-at-home orders were lifted but people continued to work from home, kids switched back-and-forth between remote and in-person classes, and so on.

We pulled calls for service data from the [Police Data Initiative](https://www.policedatainitiative.org/datasets/) and created a "weekly" time-series dataset consisting of 156 seven-day periods - starting on January 1, 2018 and ending on December 27, 2020.[^2] We ran interrupted-time series analyses for each jurisdiction separately, using the week that stay-at-home orders went into effect as the interruption point. The figure below displays the results (right click and open in a new tab for better resolution).[^3]

![ppr_fig2](/img/ppr_dvcfs_fig2.png)

**Key findings:**

* In every jurisdiction, other (non-DV) citizen-intiated calls for service declined during stay-at-home orders. 
* Every jurisdiction but Cincinnati experienced a significant spike in DV calls for service during stay-at-home orders.
* After stay-at-home orders were lifted, DV calls for service declined or remained fairly stable throughout the remainder of 2020 in every jurisdiction but Salt Lake City - where they increased.

At the time of this writing, a new, more contagious strain of the coronavirus is spreading throughout the population as we race to distribute the vaccines. In the event new rounds of stay-at-home orders are necessary to slow the spread, our findings (and prior work) suggest we could see a spike in DV calls for service in many jurisdictions.

In the paper, we get into the practical implications of these findings. I'll link a non-paywalled post-print here once the article is live. Hit me up in the meantime if you'd like a copy. 

One last thing: we submitted this on January 11, 2021 as a "rapid communication" to *Police Practice & Research*. As promised, the review process was lightning fast. We got an R&R on January 17th, resubmitted a few days later, and were notified it was accepted on January 25th. Hats off to Mike White, Laura Huey, and the reviewers they've been calling on for holding up their end of the deal. I've had papers sit in peer-review purgatory for months, sometimes years, so this was truly refreshing. 


[^1]: A handful of earlier studies have already shown that domestic/family violence calls did in fact increase in many jurisdictions during stay-at-home orders. See, e.g., [Bullinger et al., 2020](https://www.nber.org/system/files/working_papers/w27667/w27667.pdf), [Campedelli et al., 2020](https://doi.org/10.1186/s40163-020-00131-8), [Leslie & Wilson, 2020](https://doi.org/10.1016/j.jpubeco.2020.104241), [Mohler et al., 2020](https://doi.org/10.1016/j.jcrimjus.2020.101692), and [Piquero et al., 2020](https://doi.org/10.1007/s12103-020-09531-7).
[^2]: Replication materials are up on my [GitHub](https://github.com/jnixy/replication-materials/tree/master/nix_richards_PPR_InPress).
[^3]: This color template is ideal for comparing/contrasting six data classes. See Cynthia Brewer et al.'s  [ColorBrewer2.0](https://colorbrewer2.org/#type=qualitative&scheme=Dark2&n=6), and use it for your own work!
