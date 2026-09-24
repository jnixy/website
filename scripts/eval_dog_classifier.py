#!/usr/bin/env python3
"""
Scope-rule regression check for the dog-shooting classifier.

Each case is a short news-style article built around one edge of the scope
rule in CLASSIFY_SYSTEM. The expected answer follows the written rule: a sworn
officer acting as police fired at a dog -> qualifies, whatever the reason for
firing or what happened afterward. Run after any change to CLASSIFY_SYSTEM,
HEADLINE_ONLY_NOTE, or OFFICIAL_RECORD_NOTE.

Added 2026-09-24 after Haiku rejected in-scope agency records with exclusions
the rule does not contain ("defense of a third party", "a dog attacking a
dog") and a news article about an officer shooting a civilian's service dog.

Usage (needs ANTHROPIC_API_KEY; ~$0.01 per full pass):
  python scripts/eval_dog_classifier.py            # each case once
  python scripts/eval_dog_classifier.py --repeat 3 # expose run-to-run flips
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_dog_shooting_tracker as g  # noqa: E402

PUB = "2026-05-12T14:00:00Z"

# (case id, expected qualifies, headline, body[, expected dog_targeted])
CASES = [
    ("defend-person", True,
     "Officer shoots dog mauling woman in her front yard",
     "Springfield police said an officer shot a pit bull Monday that was attacking a 62-year-old "
     "woman in her front yard on Elm Street. Officers responding to a 911 call found the dog biting "
     "the woman's arm and fired two rounds, killing the dog. The woman was hospitalized in stable "
     "condition, according to Springfield Police Department spokesperson Lt. Dana Ruiz."),
    ("dog-on-dog", True,
     "Police fire at German shepherd attacking a leashed dog",
     "A Dayton police officer fired twice at a German shepherd Monday afternoon after it attacked "
     "a leashed dog being walked on Hess Street, the Dayton Police Department said. The shepherd "
     "ran off and was not found. The smaller dog was taken to a veterinarian for bite wounds."),
    ("missed-shot", True,
     "Deputy fires at charging dog during welfare check, misses",
     "A Marion County sheriff's deputy fired one round at a dog that charged him during a welfare "
     "check on Monday, the sheriff's office said. The shot missed and the dog ran back into the "
     "house. No one was injured."),
    ("service-dog", True,
     "Family says police shot their son's autism service dog",
     "A Tacoma family says a Tacoma police officer shot and killed their son's autism service dog "
     "on Monday while officers were serving an arrest warrant on a neighbor at their duplex. The "
     "department confirmed an officer fired at the dog, saying it ran at officers in the yard."),
    ("charged-after", True,
     "Trooper charged with animal cruelty for shooting dog during traffic stop",
     "A state trooper was charged Monday with animal cruelty for shooting a dog during a February "
     "traffic stop on Route 9, the district attorney announced. Video shows the trooper, on duty and "
     "in uniform, firing at the leashed dog as its owner held it. The dog survived."),
    ("offduty-as-police", True,
     "Off-duty officer shoots dog attacking child, identifies himself as police",
     "An off-duty Houston police officer shot a dog that was attacking a 7-year-old boy at a park "
     "on Monday, police said. The officer identified himself as police, ordered bystanders back, "
     "fired at the dog, and then held the scene until on-duty officers arrived."),
    ("warrant-no-knock", True,
     "SWAT officers shoot two dogs during drug raid",
     "Officers with the Kansas City Police Department SWAT team shot two dogs while executing a "
     "no-knock search warrant on Monday morning, a department spokesperson said. One dog died; the "
     "other was taken to animal control. The owner said the dogs were in their kennels."),
    # Scope widened 2026-09-24: any dog hit by on-duty police gunfire counts,
    # flagged dog_targeted=no when the rounds were aimed at someone else.
    ("own-k9", True,
     "Officer accidentally shoots his own K-9 partner during standoff",
     "A Mesa police K-9, Rex, was wounded Monday when his handler's round struck him during a "
     "shootout with a barricaded suspect, the department said. Rex is expected to recover.",
     "no"),
    ("stray-family-dog", True,
     "Family dog killed by police bullet during shootout with suspect",
     "A family's Labrador was killed Monday when a round fired by an Omaha police officer at an "
     "armed suspect in a backyard on Maple Street struck the dog, the Omaha Police Department said. "
     "The suspect was wounded and arrested.",
     "no"),
    # --- should be rejected ---
    ("k9-shot-by-suspect", False,
     "Police K-9 wounded after suspect opens fire on officers",
     "A Tulsa police K-9 was shot and wounded Monday when a burglary suspect opened fire on officers "
     "who had tracked him to a shed, police said. Officers did not return fire; the suspect was "
     "arrested. The K-9 is recovering."),
    ("offduty-personal", False,
     "Off-duty officer shoots pit bull that charged his family on a walk",
     "An off-duty Philadelphia police officer out for a walk with his wife, children, and their dog "
     "shot a pit bull with his personal handgun on Monday after it ran out of a yard and charged "
     "them, police said. The pit bull was struck in the leg."),
    ("animal-control", False,
     "Animal control officer shoots aggressive dog",
     "A county animal control officer shot and killed an aggressive dog on Monday after it bit two "
     "people, the county animal services department said. No police were involved."),
    ("deer-mercy", False,
     "Officer puts down deer struck by car",
     "A Lincoln police officer euthanized a deer with his service weapon Monday night after it was "
     "struck by a car on 27th Street, police said. A dog belonging to the driver was unhurt."),
    ("retired", False,
     "Retired officer shoots neighbor's dog in property dispute",
     "A retired Dallas police officer was arrested after shooting his neighbor's dog during a "
     "dispute over a fence line on Monday, police said."),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeat", type=int, default=1, help="run each case N times")
    args = ap.parse_args()

    client = g.get_client()
    failures = 0
    for case in CASES:
        cid, expected, title, body = case[:4]
        want_targeted = case[4] if len(case) > 4 else None  # checked only where given
        results, targeted = [], []
        for _ in range(args.repeat):
            fields = g.classify_article(client, title, body, f"https://example.com/{cid}", PUB)
            results.append(None if fields is None else bool(fields.get("qualifies")))
            targeted.append(fields.get("dog_targeted") if fields else None)
        ok = all(r == expected for r in results)
        if want_targeted:
            ok = ok and all(t == want_targeted for t in targeted)
            results = [f"{r}/{t}" for r, t in zip(results, targeted)]
        failures += 0 if ok else 1
        last = fields.get("reason", "") if fields else "API error"
        print(f"{'PASS' if ok else 'FAIL'}  {cid:18s} expected={expected!s:5s} got={results}  {last[:90]}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} cases passed (x{args.repeat} runs each).")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
