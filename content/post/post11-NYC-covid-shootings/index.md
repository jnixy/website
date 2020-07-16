---
authors:
- admin
- Kyle McLean
- John Hall
categories: []
date: "2020-06-03T09:30:00Z"
draft: false
featured: false
image:
  caption: "Image by [Pom'](https://www.flickr.com/photos/pom-angers/) at [Flickr](https://flic.kr/p/S1YbWf)"
  focal_point: "center"
projects: []
subtitle: ""
summary: 
tags:
- Police
- Gun violence
- LEADS
- COVID-19
- Public health

title: "No Significant Decline in NYC Shootings Amidst COVID-19 Pandemic"
url_pdf: ""
---

On March 1, 2020, New York City reported its first confirmed case of COVID-19. Eleven days later, Mayor de Blasio declared a state of emergency. By mid-March, the most populous city in America had essentially shut down. Schools, libraries, gyms, theaters, churches and nightclubs closed. Major sporting events and concerts were cancelled. Restaurants were limited to take-out and delivery only. Non-essential gatherings of any size were prohibited, and New Yorkers were ordered to “shelter in place.” As of today, the city is reporting over 205,000 confirmed cases and over 16,000 deaths.

How have these significant disruptions to daily life in NYC affected crime, and in particular, **shootings**? Other cities have witnessed an array of trends in **gun violence** (i.e., crimes committed with a firearm) amidst the COVID-19 pandemic. In Dallas and Tucson, for example, gun violence increased despite decreases in other violent crimes. In Nashville and Philadelphia, gun violence remained stable. Meanwhile, in other cities – including Baltimore, Chicago, Los Angeles, New Orleans, and Washington, DC – gun violence decreased.<sup>[1]</sup> Here in Omaha, the local police department reports that shootings and “shots fired” calls have increased.<sup>[2]</sup> 

As an epicenter of the COVID-19 outbreak in the US, NYC has experienced a more drastic shock to daily life than other cities. For example, a state serology study of COVID-19 in New York found that 1 in 4 people in NYC had antibodies that suggested they had been infected. This compared to antibody prevalence of 3.4% in New York state (excluding NYC, Long Island, Westchester, and Rockland).<sup>[3]</sup> Consider also that a county health department study of serology in Los Angeles found a prevalence of antibodies in 4.1% of adults in LA county.<sup>[4]</sup> Clearly, NYC has been hit harder by COVID-19 than other major cities, so the effects of the pandemic on crime may be more pronounced there.

Curious about what happened in NYC, I teamed up with NIJ LEADS Scholar John Hall (NYPD) and fellow LEADS Academic [Kyle McLean](https://twitter.com/Clempoliceprof) (Clemson University). First, we simply examined trends in shootings in 2020. There had been 341 shootings as of June 2nd, with the daily total ranging from 0 to 9 with a mean of 2.2: 

![NYC1](/img/nyc_shootings_1.png)

The daily total bounces around so much that it’s difficult to draw any conclusions about the trend. So, we next smoothed out some of the noise by plotting the 7-day running mean:

![NYC2](/img/nyc_shootings_2.png)

It looks like there was a brief uptick following the first reported COVID-19 case, then a brief decline following the state of emergency declaration, and an upward trend throughout April and May.

Of course, this can be *highly misleading* for at least two reasons. First, the data are still noisy. We really need more data before we can draw any meaningful conclusions about trends. Second, we don’t know what might’ve happened in 2020 *absent* the COVID-19 pandemic. Shootings undoubtedly increase in New York every year as the weather gets warmer. So we need a reasonable counterfactual to compare against in order to make sense of what we’ve observed in 2020 thus far. 

With this in mind, we next examined trends in shootings from January 1, 2016 through June 2, 2020. In the graph below, we’ve imposed the 2020 trend line (as of June 2nd) over the trend lines for each of the previous four years. Here, the lines represent 7-day running means, to smooth out some of the day-to-day noisiness. 

![NYC3](/img/nyc_shootings_3.png)

Viewed in this way, the recent uptick NYC has observed in 2020 doesn’t appear inconsistent with what happened each of the last four years. So while we can confidently say that shootings **haven’t declined** amidst the COVID-19 pandemic, the data don’t really suggest that shootings are significantly up, either. 

Let's all agree to be skeptical of vague hot-takes like **“Crime is down!”** It’s way more nuanced – and localized – than that.<sup>[5-9]</sup> 

<div class="alert alert-warning" role="alert">
  <p style="text-align:center"> You can download incident-level shooting data from the NYPD <a href="#" class="https://www1.nyc.gov/site/nypd/stats/crime-statistics/citywide-crime-stats.page">here</a>.</p>
</div>

**References**  
1. Daniel Nass (2020, Apr 29). [Shootings are a glaring exception to the coronavirus crime drop](https://www.thetrace.org/2020/04/coronavirus-gun-violence-stay-at-home-orders/). *The Trace*.  
2. Sarah Fili (2020, Apr 30). [OPD: Shootings, shots fired calls rise amid COVID-19 pandemic](https://www.ketv.com/article/opd-shootings-shots-fired-calls-rise-amid-covid-19-pandemic/32339922). *KETV Omaha*.  
3. Yasemin Saplakoglu (2020, Apr 23). [1 in 5 people tested in New York City had antibodies for the coronavirus](https://www.livescience.com/covid-antibody-test-results-new-york-test.html). *Live Science*.  
4. Los Angeles County Department of Public Health (2020, Apr 20). [USC-LA County study: Early results of antibody testing suggest number of COVID-19 infections rar exceeds number of confirmed cases in Los Angeles County](http://publichealth.lacounty.gov/phcommon/public/media/mediapubhpdetail.cfm?prid=2328).  
5. [Matthew Ashby](https://twitter.com/LessCrime) (2020). [Initial evidence on the relationship between the coronavirus pandemic and crime in the United States](https://crimesciencejournal.biomedcentral.com/articles/10.1186/s40163-020-00117-6). *Crime Science*, 9(6).  
6. [Gian Maria Campedelli](https://twitter.com/CampedelliGian) et al. (2020, Mar 23). [Exploring the effect of 2019-nCoV containment policies on crime: The case of Los Angeles](https://osf.io/gcpq8/). *OSF Preprints*.  
7. George Mohler et al. (2020). [Impact of social distancing during COVID-19 pandemic on crime in Los Angeles and Indianapolis](https://www.sciencedirect.com/science/article/pii/S0047235220301860). *Journal of Criminal Justice*, 68(101692).  
8. John McDonald & Steven Balkin (2020, Apr 10). [The COVID-19 and the decline in crime](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3567500). *SSRN*.    
9. Neil MacFarquhar & Serge Kovaleski (2020, May 26). [A pandemic bright spot: In many places, less crime](https://www.nytimes.com/2020/05/26/us/coronavirus-crime.html?referringSource=articleShare). *The New York Times*.
