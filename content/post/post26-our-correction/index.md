---
title: "Our Correction for *When Police Pull Back*"
categories: []
date: '2024-11-08T09:00:00Z'
featured: false
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
- George Floyd
- Neighborhoods
- Violence
- COVID-19
authors: 
- admin
url_pdf: ""
draft: false
---

**BOTTOM LINE: Yes, there was a merge error in our research note, ["When Police Pull Back"](https://doi.org/10.1111/1745-9125.12363). However, correcting it did not render all our key findings nonsignificant as Jacob Kang-Brown claimed. In his replication, Jacob calculated our spatial lag variable differently, thereby reintroducing the endogeneity problem we designed our analysis to avoid. We are correcting, not retracting, the research note.**

***

## What happened? 

We made an honest mistake. We own that. 

## Why did it take "so long" for us to respond? 

Verifying there was a merge error was quick and easy, of course. But what Jacob's Twitter thread didn't tell you is that he was actually not able to reproduce our published tables *before* he fixed the merge errors and reran the analyses. Thus, *he'd done something wrong*. So we couldn't just take his word that "a retraction was in order." It took us a bit more time to figure out (1) what he did wrong (such that he couldn't reproduce our tables) and (2) if his assertion that our results hinged entirely on the merge error was correct. 

**That said, we submitted our detailed response to the Editors on May 16th - just 30 days after Jacob first emailed us.**  

The Editors of *Criminology* decided to have an independent reviewer evaluate our response (and code), and asked us not to share our memo publicly in the meantime. We chose to respect their request. I've put a detailed timeline in a [table](#timeline) near the bottom of this post.

## Why was some of your data and code missing from the replication materials you posted?

Honest oversight. This project was 2+ years in the making, involving many datasets and lots of code strewn about as we worked through the analysis. I'm new to open science, and learning the best I can as I go. When I Frankensteined our code back together for sharing publicly, I missed a few chunks needed to create the weather, AQI, and OpenTable control variables. Along with the correction, we'll be adding those chunks of code and datasets to our dataverse repository. 

Jacob implied there was something sinister about the omission: 

![jkb](jkb-tweet.png)

Yet when he [first contacted me](#timeline) and asked about a dataset he couldn't find, I immediately pointed him to it. Why he didn't reach back out when he noticed others were missing is beyond me. But if we were trying to hide something, why would we make *any* of our data and code available (since it is not required)? It doesn't make sense. 

## Why should we believe your version of the story over Jacob's?

We showed our work, which has been inspected and reproduced by a neutral third party.

## Original and Corrected Results

for Table 1, Panel 2 (DV = Violent Crime):

| Variable         	| Original Association 	| Corrected Association 	|
|:-----------------	|:---------------------	|:----------------------	|
| Pedestrian stops 	| b = -.022***         	| b = -.009***          	|
| Vehicle stops    	| b = -.002*           	| b = -.002             	|
| Drug arrests     	| b = -.005            	| b = .013              	|
| Disorder arrests 	| b = -.021            	| b = -.020             	|

for Table 1, panel 3 (DV = Property crime):

| Variable         	| Original Association 	| Corrected Association 	|
|:-----------------	|:---------------------	|:----------------------	|
| Pedestrian stops 	| b = .002             	| b = -.005*            	|
| Vehicle stops    	| b = .001             	| b = -.0003            	|
| Drug arrests     	| b = -.027**          	| b = -.012             	|
| Disorder arrests 	| b = -.014            	| b = .003              	|

## Some concluding thoughts

First, a lot of people - including many academics - were *quick* to believe Jacob without actually scrutinizing his work or at least waiting until it had been reviewed. The neighborhood merge error mostly affected Level 2 control variables **which were not time varying**. Careful readers might have been skeptical that fixing a time invariant control variable could completely wash away all the relationships between our Level 1 policing mediators and Level 1 crime outcomes, all of which varied across weeks. In any event, I hope news that our article is being corrected (not retracted) will travel as far and as fast as Jacob's tweets (264K views, 1100 likes, 341 retweets). I'm not holding my breath, though. 

Second, I think this is a great example of how not to do open science. In a field where sharing data and code isn't the norm, and some are fearful of doing so, this will only affirm their fears and slow progress. If Jacob was truly interested in "the spirit of collaboration," he should've reached back out to me after he couldn't reproduce our tables (i.e., before fixing the merge) - like I respectfully asked. We probably would've identified the discrepancy much faster, issued a correction, and moved on. Instead, he prematurely blasted us on Twitter, 28 days after he notified us of the error. This predictably led to a Twitter pile-on, with people openly questioning our integrity ([academic malfeasance!](https://x.com/avitale/status/1791136497883644244)), the journal's integrity, and the entire field's credibility ([criminology isn't a real science!](https://x.com/JooHyun_Kang/status/1790676346139553836)). It didn't have to be that way.[^1]

Regardless, I'll continue to embrace and advocate for transparency and open science practices. Better to identify mistakes and correct the scientific record than pretend humans don't make mistakes from time to time, in my opinion.

{{% alert note %}}
<p style="text-align:center"> We'll be sharing a longer-form essay on the importance of open science in criminology soon.</p>
{{% /alert %}}

## Timeline {#timeline}

|           	|                                                                                                                                                                                                                     	|
|-----------	|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------	|
| 3/28/2024 	| JKB emailed the lead author (Nix) asking about a dataset that was missing from the OSF repository.                                                                                                                  	|
|           	| We responded within a few hours, directing him to the Harvard Dataverse repository, and twice asked him to let us know if the materials we provided helped resolve his issue. He did not respond to either request. 	|
| 4/16/2024 	| At the request of the editors, JKB emailed all coauthors informing us of the error he identified and that he has requested a retraction.                                                                            	|
|           	| We responded the next day promising to respond in a timely manner.                                                                                                                                                  	|
| 4/24/2024 	| JKB emails the authorship team again to ask for an update.                                                                                                                                                          	|
|           	| We responded the same day, explaining that it was a busy time of year for academics, but promising again that we were taking his claims seriously.                                                                  	|
| 5/3/2024  	| JKB emails the authorship team and the editors demanding a substantive response or clear timeline by May 7th.                                                                                                       	|
|           	| A Co-Lead Editor responded, informed JKB of an editorial meeting the following week where they would consult COPE guidelines, and suggested JKB wait for that.                                                      	|
| 5/7/2024  	| Editors request a written response from us by May 31st.                                                                                                                                                             	|
| 5/14/2024 	| JKB tweets.                                                                                                                                                                                                         	|
| 5/16/2024 	| We provide our written response to the editors.                                                                                                                                                                     	|
| 6/1/2024  	| JKB emails the entire editorial team stating he never received our written response and asks them to share it.                                                                                                      	|
| 6/3/2024  	| Co-Lead Editor shares our written response with JKB and informs him of their decision to conduct an independent analysis.                                                                                           	|
| 8/19/2024 	| Anonymous reviewer confirms they can reproduce our analysis.                                                                                                                                                        	|


[^1]: "But Justin, didn't you publicly go after that public health paper one time? Doesn't this make you a hypocrite?" I don't think so, because in that case I initially reached out to one of the authors with a question which they blew off, then followed journal protocol and submitted a correspondence which was published but again blown off by the authors, *then* wrote up a replication piece and shared it online. And yet, I acknowledge that if I could go back and do it again I would probably handle it differently. 