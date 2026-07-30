#!/usr/bin/env python3
"""
Build Lloyd category-only annotated dictionary.

ONLY words in these groups get values:
  +10$  coding, hacking, english-structure, slang, attitude, humor
  +7$   pattern indicators / relational connectors

All other words have NO value and are omitted.
"""

from __future__ import annotations
from pathlib import Path

CODING = set("""
code coding program programming programmer function variable class object method
array list string integer boolean float loop while for if else return import module package
library api sdk compiler debug debugging bug error exception stack heap memory pointer null
none true false async await promise callback thread process server client database sql query
table index cache buffer byte bit binary hex ascii unicode json xml html css javascript
python java rust golang typescript ruby php swift kotlin script syntax parse parser token
lexer regex algorithm data structure tree graph hash map set queue sort search recursion
iterate iterator generator decorator closure lambda interface type typing generic template
macro namespace repo repository commit branch merge pull push clone git github gitlab deploy
deployment docker container kubernetes cloud aws azure linux unix shell bash terminal
command cli gui frontend backend framework react vue angular node npm pip cargo build
compile runtime virtual machine learning model neural network tensor gradient train training
dataset feature label predict inference embedding attention transformer tokenizer gpu cpu ram
disk file path directory folder input output log logging test unit integration mock assert
refactor optimize performance latency throughput bandwidth protocol http https tcp udp socket
request response header cookie session auth authentication authorization oauth jwt encrypt
decrypt password username user admin root sudo permission access role policy
""".split())

HACKING = set("""
hack hacker hacking exploit vulnerability payload malware virus trojan worm
ransomware phishing spoof inject injection xss csrf sqli overflow shellcode rootkit backdoor
keylogger botnet ddos dos bruteforce crack cracker rainbow zeroday cve patch firewall ids ips
siem penetration pentest pentesting redteam blueteam social engineering osint recon
reconnaissance scan scanner nmap metasploit wireshark proxy vpn tor darknet deepweb breach
leak dump credential privilege escalation lateral movement persist persistence exfil obfuscate
reverse disassemble decompile firmware jailbreak bypass hook dll sandbox evasion antivirus
defender endpoint threat actor apt campaign ioc
""".split())

STRUCTURE = set("""
noun verb adjective adverb pronoun preposition conjunction interjection subject
object predicate clause phrase sentence paragraph article determiner tense past present future
plural singular possessive comparative superlative active passive voice mood indicative
imperative subjunctive infinitive gerund participle auxiliary modal grammar syntax semantics
punctuation comma period colon semicolon apostrophe hyphen the a an is are was were be been
being have has had do does did will would shall should can could may might must of to in for
on with at by from as into about like through over between out against during without under
around among and but or nor yet so although while unless when where why how who whom whose
which that this these those i you he she it we they me him her us them my your his its our
their not no yes very too also just only even still already really
""".split())

SLANG = set("""
yo sup bruh bro dude homie fam squad lit fire bussin cap nocap fr frfr ong bet
lowkey highkey sus salty mid slay slaps vibe vibes rizz sigma skibidi gyatt based cringe ratio
goat goated npc cope seethe aura drip flex clout stan tea spill periodt snatched lmao lmfao
lol rofl omg wtf smh fyp irl dm ghost ghosted simp simping thirsty downbad valid delulu
unalive iykyk rn nvm deadass finna gonna wanna gotta yall sis queen king bestie bff bae woke
trash cooked brainrot
""".split())

ATTITUDE = set("""
attitude personality confident confidence swagger swag bold brave fearless fierce
savage ruthless relentless ambitious driven motivated hustle grind grinding boss leader alpha
independent stubborn proud ego arrogant cocky humble chill relaxed calm cool cold icy stoic
intense passionate aggressive passive assertive dominant loyal honest blunt direct sarcastic
witty clever smart dumb stupid genius chaotic wild crazy insane mad angry happy sad moody
energy presence charisma charm style edge edgy dark light positive negative toxic healthy real
fake authentic genuine extra dramatic petty messy clean focus discipline lazy productive
winner loser champion underdog rebel
""".split())

HUMOR = set("""
joke jokes funny hilarious comedy comedian humor laugh laughing pun puns sarcasm
ironic irony satire parody meme memes shitpost troll trolling roast roasted burn gallows
morbid twisted sick disturbing offensive crude adult nsfw dirty raunchy sexual innuendo
punchline setup sketch improv wit corny cheesy unfunny deadpan absurdist surreal wholesome
cursed blessed chaos goblin feral unhinged deranged psychotic maniac evil villain spoiler
banter tease teasing
""".split())

PATTERN = set("""
first then next after before follows followed preceded sequence step steps process
order progression cycle repeat repeats repeated pattern patterns finally last previously
afterward afterwards eventually subsequently initially beginning end ending phase stage series
same similar similarity compared comparison differs differ difference different opposite
contrast contrasts both identical matching match matches parallel alike unlike versus vs equal
equals equivalent analogous resembles resemble because therefore cause causes caused effect
effects reason reasons results result leads lead leading conditional whenever since hence thus
consequently accordingly so if then unless whether implies imply implication outcome outcomes
consequence consequences always often sometimes never usually typically generally frequently
rarely seldom tends tend tendency habit habits custom routine routines regularly occasionally
constantly consistently periodically more less increase increases increased decrease decreases
decreased grow grows grew growing shrink shrinks expand expands reduce reduces reduced rise
rises fall falls higher lower greater smaller change changes changed shift shifts shifted
larger bigger fewer most least connects connect connected connection connections relates relate
related relationship relationships linked link links associated associate association bond bonds
tie ties interaction interactions involves involve involved affects affect affected influences
influence influenced determines determine determined depends depend dependent independent
correlation correlates
""".split())

PLUS10 = CODING | HACKING | STRUCTURE | SLANG | ATTITUDE | HUMOR
PLUS7 = PATTERN - PLUS10


def main():
    out = Path(__file__).parent / "special_plus10s.txt"
    lines = [
        "# Lloyd Category Dictionary — ONLY valued words",
        "# +10$ = coding/hacking/structure/slang/attitude/humor",
        "# +7$  = pattern indicators / relational connectors",
        "# All other words have NO value (omitted)",
        "#",
    ]
    for w in sorted(PLUS10):
        lines.append(f"∆{w}+10$∆")
    for w in sorted(PLUS7):
        lines.append(f"∆{w}+7$∆")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  +10$ words: {len(PLUS10)}")
    print(f"  +7$  words: {len(PLUS7)}")
    print(f"  total valued: {len(PLUS10) + len(PLUS7)}")
    print("  non-category words: 0 (no value)")


if __name__ == "__main__":
    main()
