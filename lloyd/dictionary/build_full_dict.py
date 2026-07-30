#!/usr/bin/env python3
"""
Build the full Lloyd annotated dictionary from SCOWL word lists.

Every word gets ∆word+N∆ math.
Category words (coding, hacking, structure, slang, attitude, humor)
get ∆word+10$∆ (importance + context spread).
All other words get ∆word+1∆.

Usage:
  python lloyd/dictionary/build_full_dict.py /path/to/scowl/final
  # or with a plain word list:
  python lloyd/dictionary/build_full_dict.py --words words.txt

Output: lloyd/dictionary/lloyd_annotated_dictionary.txt
"""

from __future__ import annotations
import argparse
from pathlib import Path

# Category banks → +10$
CODING = set("""
code coding codes coded coder program programs programming programmer function functions
variable variables class classes object objects method methods array arrays list lists
string strings integer boolean float loop while for else return import module package
library api sdk compiler debug debugging bug error exception stack heap memory pointer
null none true false async await promise callback thread process server client database
sql query table index cache buffer byte bit binary hex ascii unicode json xml html css
javascript python java rust golang typescript ruby php swift kotlin script syntax parse
parser token lexer regex algorithm data structure tree graph hash map set queue sort
search recursion iterate iterator generator decorator closure lambda interface type
typing generic template macro namespace repo repository commit branch merge pull push
clone git github gitlab deploy deployment docker container kubernetes cloud aws azure
linux unix shell bash terminal command cli gui frontend backend framework react vue
angular node npm pip cargo build compile runtime virtual machine learning model neural
network tensor gradient train training dataset feature label predict inference embedding
attention transformer tokenizer gpu cpu ram disk file path directory folder input output
log logging test unit integration mock assert refactor optimize performance latency
throughput bandwidth protocol http https tcp udp socket request response header cookie
session auth authentication authorization oauth jwt encrypt decrypt password username
user admin root sudo permission access role policy
""".split())

HACKING = set("""
hack hacks hacked hacking hacker hackers exploit vulnerability payload malware virus
trojan worm ransomware phishing spoof inject injection xss csrf sqli overflow shellcode
rootkit backdoor keylogger botnet ddos dos bruteforce crack cracker rainbow zeroday cve
patch firewall ids ips siem penetration pentest pentesting redteam blueteam social
engineering osint recon reconnaissance scan scanner nmap metasploit wireshark proxy vpn
tor darknet deepweb breach leak dump credential privilege escalation lateral movement
persist persistence exfil obfuscate reverse engineering disassemble decompile firmware
jailbreak bypass hook dll sandbox evasion antivirus defender endpoint threat actor apt
campaign ioc
""".split())

STRUCTURE = set("""
noun verb adjective adverb pronoun preposition conjunction interjection subject object
predicate clause phrase sentence paragraph article determiner tense past present future
plural singular possessive comparative superlative active passive voice mood indicative
imperative subjunctive infinitive gerund participle auxiliary modal copula complement
modifier relative dependent independent compound complex simple fragment syntax semantics
morphology phonology phonetics orthography punctuation comma period question mark
exclamation colon semicolon apostrophe quotation hyphen dash capital lowercase uppercase
grammar grammatical the a an is are was were be been being have has had do does did will
would shall should can could may might must of to in for on with at by from as into about
like through after over between out against during without before under around among and
but or nor yet so because although while if unless since when where why how who whom whose
which that this these those i you he she it we they me him her us them my your his its our
their mine yours hers ours theirs myself yourself himself herself itself ourselves
themselves not no yes very too also just only even still already always never often
sometimes usually really
""".split())

SLANG = set("""
yo sup bruh bro dude homie fam squad lit fire bussin buss cap nocap fr frfr ong bet
lowkey highkey sus salty mid slay slaps vibe vibes vibing rizz sigma skibidi gyatt fanum
ohio based cringe ratio goat goated npc grass cope seethe mald skill issue aura drip fit
flex clout stan ship tea spill periodt snatched wig af asf imo imho tbh idk idc ily lmao
lmfao lol rofl brb gtg omg wtf smh fyp irl dm ghost ghosted simping simp thirsty downbad
valid invalid ate assignment delulu unalive iykyk rn nvm deadass finna gonna wanna gotta
ain yall ya sis queen king bestie bff bae boo shawty shorty woke trash garbage cooked
finished built different hits fax facts locked brainrot
""".split())

ATTITUDE = set("""
attitude personality confident confidence swagger swag bold brave fearless fierce savage
ruthless relentless ambitious driven motivated hustle grind grinding boss leader alpha
sigma lone wolf independent stubborn proud ego arrogant cocky humble chill relaxed calm
cool cold icy stoic intense passionate aggressive passive assertive dominant submissive
loyal honest blunt direct sarcastic witty clever smart dumb stupid genius chaotic orderly
wild crazy insane mad angry happy sad moody energy presence charisma charm style flavor
sauce edge edgy dark light positive negative toxic healthy real fake authentic genuine
phony tryhard effortless natural forced extra dramatic petty messy clean organized random
deliberate intentional focus discipline lazy productive winner loser champion underdog
rebel conformist
""".split())

HUMOR = set("""
joke jokes funny hilarious comedy comedian humor humour laugh laughing lol lmao lmfao
rofl pun puns sarcasm ironic irony satire parody meme memes shitpost troll trolling roast
roasted burn burns dark gallows morbid twisted sick disturbing offensive edgy crude adult
nsfw dirty raunchy sexual innuendo double entendre punny dad knock punchline setup bit
sketch stand improv wit witty clever corny cheesy cringe unfunny deadpan dry absurdist
surreal wholesome cursed blessed chaos goblin mode feral unhinged deranged psychotic
maniac evil villain arc plot twist spoiler punch banter tease teasing rib ribbing
""".split())

SPECIAL = CODING | HACKING | STRUCTURE | SLANG | ATTITUDE | HUMOR


def annotate(word: str) -> str:
    w = word.lower().strip()
    if w in SPECIAL:
        return f"∆{w}+10$∆"
    return f"∆{w}+1∆"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", help="SCOWL final/ dir or words file")
    ap.add_argument("--words", help="plain word list file")
    ap.add_argument("-o", "--output", default=None)
    args = ap.parse_args()

    words: set[str] = set()
    if args.words:
        words |= {ln.strip().lower() for ln in Path(args.words).read_text().splitlines() if ln.strip()}
    elif args.source:
        p = Path(args.source)
        if p.is_dir():
            for f in p.glob("english-words.*"):
                words |= {ln.strip().lower() for ln in f.read_text(errors="ignore").splitlines()}
            for f in p.glob("american-words.*"):
                words |= {ln.strip().lower() for ln in f.read_text(errors="ignore").splitlines()}
        else:
            words |= {ln.strip().lower() for ln in p.read_text().splitlines() if ln.strip()}
    else:
        # fallback: use special only + minimal seed
        words = set(SPECIAL)

    words = {w for w in words if w and w.replace("'", "").isalpha()}
    sorted_words = sorted(words)

    out = Path(args.output) if args.output else Path(__file__).parent / "lloyd_annotated_dictionary.txt"
    counts = {"special": 0, "other": 0}
    lines = []
    for w in sorted_words:
        line = annotate(w)
        lines.append(line)
        if "+10$" in line:
            counts["special"] += 1
        else:
            counts["other"] += 1

    header = f"""# Lloyd Annotated Dictionary — COMPLETE SCOWL COPY
# Every word has importance math: ∆word+N∆ or ∆word+N$∆
# $ = context amplifier (spread importance to nearby words)
# Category words (coding/hacking/structure/slang/attitude/humor) = +10$
# All other words = +1
# Ranking: +numbers > 0 > -numbers
# TOTAL: {len(lines)}  special(+10$): {counts['special']}  other(+1): {counts['other']}
#
"""
    out.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(lines)} words)")


if __name__ == "__main__":
    main()
