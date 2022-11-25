---
title: "A Multi-Site Study of Firearms Displays by Police at Use of Force Incidents"
authors:
- Timothy Cubitt
- admin
date: "2022-10-25T11:00:00Z"
output: 
featured: no
image:
  caption: "Image by [Jan](https://pixabay.com/users/janjf93-3084263/) on [Pixabay](https://pixabay.com/vectors/weapon-handgun-run-mouth-1613997/)"
  focal_point: smart
  preview_only: no
doi: 10.1177/10986111221136230
projects: []
publication: '*Police Quarterly*'
publication_short: PQ
publication_types: 
- "2"
publishDate: "2022-11-25T09:00:00Z"
slides: ""
summary: ""
tags:
- Police
- Use of Force
- Machine Learning
- Firearms
- External Validity
abstract: "The power to use force is a defining characteristic of policing, one that is accompanied by a responsibility to exercise these powers in the circumstances deemed necessary. This study analyzes data from four policing agencies to predict the likelihood of an officer drawing and pointing their firearm at a use of force incident. Findings suggest that situational factors were important in influencing whether an officer may draw and point their firearm. However, a priming effect, in which officers were more likely to draw their firearms when dispatched to an incident, may also be present. The rate that officers drew and pointed their firearms varied between jurisdictions, as did the nature of the incidents. Caution should be exercised in generalizing the results of single-site studies on police use of force, or introducing research into policy beyond the jurisdiction in which it was performed."
url_code: ""
url_dataset: ""
url_pdf: "https://digitalcommons.unomaha.edu/cgi/viewcontent.cgi?article=1147&context=criminaljusticefacpub"
url_poster: ""
url_project: ""
url_slides: ""
url_source: ""
url_video: ""
---

**Summary**

Only [54% of local agencies](https://bjs.ojp.gov/content/pub/pdf/lpdpp16.pdf) require their officers to report when they use this specific type of force. Prior research in [Dallas](https://doi.org/10.1177/1525107118759900) and [New Orleans](https://doi.org/10.1016/j.jcrimjus.2020.101775) suggests officers discharge their firearms upon displaying them only about 1 to 3% of the time. In other words, for every 100 instances of officers displaying their firearms, they discharge them roughly 1 to 3 times. Understanding what might have influenced officers' decision to **not shoot** in those other 97 to 99 instances is critical as we seek a more holistic understanding of police use of deadly force. So [Tim Cubitt](https://www.utas.edu.au/profiles/staff/tiles/tim-cubitt) and I pulled use of force data for Austin, Baltimore, Dallas, and Portland from the [Police Data Initiative](https://www.policedatainitiative.org/datasets/) to model the factors associated with **displaying (but not shooting) firearms**. 

The first noteworthy finding was simply the variation we observed across agencies. Austin's data suggested officers displayed their firearms in ~4% of use of force incidents. Meanwhile, in Baltimore and Dallas, officers displayed their firearms in ~15% of incidents. 

After some cleaning, Tim ran random forest and logistic regression models predicting these outcomes. Both models successfully predicted the outcome ~75% of the time (see Fig. 1).

![fig1](fig1.png)

No big surprises in terms of the significant predictors, IMO. Service type, reported motivation for using force, arrest made, officer tenure, and officer injury all seem to matter. Black citizens in these jurisdictions were no more/less likely than White citizens to have police display their firearms at UOF incidents. However, Asian and Hispanic citizens were significantly more likely to experience this outcome than White citizens.

There's a lot more in the article, which you can download for free [here](https://digitalcommons.unomaha.edu/cgi/viewcontent.cgi?article=1147&context=criminaljusticefacpub). Meantime, kudos to these agencies for having this reporting requirement (which [multiple](https://doi.org/10.1111/puar.12738) [studies](http://dx.doi.org/10.1136/injuryprev-2020-043932) suggest reduce police shootings without endangering officers) and posting their data online. These kinds of investigations aren't possible if the data aren't collected or made accessible. 
