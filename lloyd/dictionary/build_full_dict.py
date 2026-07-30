#!/usr/bin/env python3
"""
Build Lloyd category-only annotated dictionary.

ONLY words in these groups get values:
  +10$  coding, hacking, english-structure, slang, attitude, humor
  +7$   pattern indicators / relational connectors

All other words have NO value and are omitted.

This script rebuilds special_plus10s.txt from the hard-coded category sets.
Overlaps between PATTERN and the +10 groups are assigned +10$.

Run: python build_full_dict.py
"""

from __future__ import annotations
from pathlib import Path

# ---------------------------------------------------------------------------
# Source-of-truth category sets (expanded)
# Keep in sync with README.md category descriptions.
# ---------------------------------------------------------------------------

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
software developer development app application fullstack devops sre cicd pipeline yaml toml
ini config configuration env environment dependency dependencies virtualenv venv conda poetry
yarn pnpm bun webpack vite babel eslint prettier tsx jsx reactjs nextjs nuxt svelte solidjs
express fastapi django flask spring boot laravel rails microservice monorepo
apiendpoint rest graphql websocket grpc protobuf avro parquet csv tsv dataframe pandas numpy
scipy pytorch tensorflow keras scikit sklearn jupyter notebook colab vscode ide editor plugin
extension linter typechecker mypy pylint flake8 black isort ruff unittest pytest jest mocha
cypress playwright selenium ci continuousintegration continuousdeployment release version
semver gitflow rebase stash conflict resolve mergeconflict dockerfile dockercompose helm
terraform ansible lambdafunction serverless faas iaas paas saas oop functional paradigm
declarative imperative polymorphism inheritance encapsulation abstraction singleton factory
observer designpattern bigo complexity timecomplexity spacecomplexity recursiondepth
stackoverflow segfault crash core heapoverflow bufferoverflow memoryleak danglingpointer
garbagecollection gc reference counting bitwise operator bitwiseand bitwiseor bitwisexor
endian littleendian bigendian serialization deserialization pickle orm sqlalchemy prisma
typeorm migration schema indexscan fullscan queryplan explain transaction isolation
concurrency mutex lock semaphore deadlock racecondition atomic atomicity parallel
frontenddev backenddev fullstackdev component components state props hook hooks
redux zustand context provider consumer render rendering virtualdom dom
useeffect usestate usememo usecallback coroutine coroutines multiprocessing
vector matrix embeddings batch epoch epochs loss optimizer relu sigmoid softmax
activation layer layers dense convolutional cnn rnn lstm gru selfattention multihead
encoder decoder dataloader preprocessing normalization standardization scaling
onehot encoding categorical numerical join joins select insert update delete
groupby orderby primarykey foreignkey constraint constraints trigger triggers
storedprocedure view views materialized schemas orms sequelize mongoose redis
mongodb postgres postgresql mysql sqlite dynamodb firestore cassandra elasticsearch
restful sse eventstream middleware router routing endpoints controller controllers
service services repositories dto entity entities models validation validator
validators serializer serializers deserializer unitests integrationtest integrationtests
e2e endtoend mocks stub stubs spy spies fixture fixtures lint linters format
formatter formatters typecheck typechecking interpret interpreter interpreters
bytecode objectcode linker linking loading loader runtimes package manager managers
lockfile lockfiles yarnlock packagelock requirements k8s chart charts
puppet chef jenkins githubactions gitlabci circleci continuous edge computing
cuda tpu npu accelerator accelerators cores hyperthreading ssd hdd storage
filesystem filesystems networking packet packets icmp dns dhcp bind listen
accept connect send recv ssl tls certificate certificates openssl oauth2 jwe jws
refresh rbac abac encryption decryption hashing aes rsa ecc bcrypt scrypt
argon2 sha256 sha512 base64 urlencode urldecode bitbucket commits branches
cherry pick stashpop pullrequest pr prs issue issues milestone milestones
commandline zsh fish powershell sublime atom neovim vim emacs marketplace
debugger breakpoint breakpoints logger loggers level levels exceptions try
catch finally raise throw throws stacktrace traceback assertion assertions
refactoring optimization scalable assembly opcodes transpile transpiler
rollup esbuild swc turbopack drizzle memcached opensearch kafka rabbitmq
nats pubsub prometheus grafana datadog sentry istio envoy pulumi cloudformation
malloc free alloc stackframe callstack dereference goroutine
""".split())

HACKING = set("""
hack hacker hacking exploit vulnerability payload malware virus trojan worm
ransomware phishing spoof inject injection xss csrf sqli overflow shellcode rootkit backdoor
keylogger botnet ddos dos bruteforce crack cracker rainbow zeroday cve patch firewall ids ips
siem penetration pentest pentesting redteam blueteam social engineering osint recon
reconnaissance scan scanner nmap metasploit wireshark proxy vpn tor darknet deepweb breach
leak dump credential privilege escalation lateral movement persist persistence exfil obfuscate
reverse disassemble decompile firmware jailbreak bypass hook dll sandbox evasion antivirus
defender endpoint threat actor apt campaign ioc cveid exploitkit kit zerodayexploit
bufferoverflow stackoverflow heapspray rop ret2libc sqlinjection xssattack csrfattack
ssrf rce remote codeexecution lfi rfi pathtraversal directorytraversal passwordhash hashcat
johntheripper rainbowtable bruteforceattack dictionaryattack phishingkit spearphishing vishing
c2 commandandcontrol beacon lateralmovement pivoting persistence mechanism implant
exfiltration dataexfil obfuscation packing unpacking sandboxescape antivirusbypass
edr endpointdetection threatintel threatintelligence indicatorofcompromise malwareanalysis
reverseengineering ghidra ida radare2 binaryninja burpsuite owasp zap kali parrot blackarch
wifi cracking wpa2 aircrack bluetooth spoofing physical security lockpicking socialengineering
pretexting 0day zeroday rce lfi rfi ssrf xxe ssti idor bac privesc
msfvenom nuclei masscan burp mitm mitmproxy john hydra
shell
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
pronouns quantifier intensifier relativeclause independentclause dependentclause
compound complex compoundcomplex modifier modifierphrase prepositionalphrase infinitivephrase
gerundphrase participlephrase absolutephrase subjectverb agreement subjectverbagreement
tenseaspect progressive perfect continuous passivevoice activevoice modalverb auxiliaryverb
linkingverb transitive intransitive ditransitive reflexive intensive demonstrative interrogative
relative coordinating subordinating correlative punctuationmark quotationmark questionmark
exclamationmark ellipsis dash capitalization capitalizationrule spelling orthography morphology
phoneme morpheme syllable lexeme lemma stem root affix prefix suffix infix derivation inflection
synonym antonym hyponym hypernym collocation idiomatic
nouns verbs adjectives adverbs pronouns prepositions conjunctions interjections
subjects predicates objects clauses phrases sentences paragraphs articles determiners
tenses voices moods participles auxiliaries modals punctuations commas periods
colons semicolons apostrophes hyphens dashes ellipses quotationmarks questionmarks
exclamationmarks phonemes morphemes syllables lexemes lemmas stems roots affixes
prefixes suffixes infixes synonyms antonyms hyponyms hypernyms collocations
""".split())

SLANG = set("""
yo sup bruh bro dude homie fam squad lit fire bussin cap nocap fr frfr ong bet
lowkey highkey sus salty mid slay slaps vibe vibes rizz sigma skibidi gyatt based cringe ratio
goat goated npc cope seethe aura drip flex clout stan tea spill periodt snatched lmao lmfao
lol rofl omg wtf smh fyp irl dm ghost ghosted simp simping thirsty downbad valid delulu
unalive iykyk rn nvm deadass finna gonna wanna gotta yall sis queen king bestie bff bae woke
trash cooked brainrot forreal rizzler rizzgod ratioed sheesh yeet noob poggers
ghosting
""".split())

ATTITUDE = set("""
attitude personality confident confidence swagger swag bold brave fearless fierce
savage ruthless relentless ambitious driven motivated hustle grind grinding boss leader alpha
independent stubborn proud ego arrogant cocky humble chill relaxed calm cool cold icy stoic
intense passionate aggressive passive assertive dominant loyal honest blunt direct sarcastic
witty clever smart dumb stupid genius chaotic wild crazy insane mad angry happy sad moody
energy presence charisma charm style edge edgy dark light positive negative toxic healthy real
fake authentic genuine extra dramatic petty messy clean focus discipline lazy productive
winner loser champion underdog rebel selfassured assured fearlessness bravery courage
hustler grinder charismatic charming focused disciplined
attitudes personalities
""".split())

HUMOR = set("""
joke jokes funny hilarious comedy comedian humor laugh laughing pun puns sarcasm
ironic irony satire parody meme memes shitpost troll trolling roast roasted burn gallows
morbid twisted sick disturbing offensive crude adult nsfw dirty raunchy sexual innuendo
punchline setup sketch improv wit corny cheesy unfunny deadpan absurdist surreal wholesome
cursed blessed chaos goblin feral unhinged deranged psychotic maniac evil villain spoiler
banter tease teasing dadjoke punny wordplay memeable shitposting darkcomedy blackcomedy standup
humour laughter comedians parodies spoilers dadjokes
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
correlation correlates sequentially sequential prior subsequent precedes following ordered
cyclic cyclical repetition iterative patterned ultimately meanwhile simultaneously concurrent
analogously likewise conversely correspondingly iff provided assuming entails contingent
""".split())

def clean(s):
    return {w.strip().lower() for w in s if w.strip() and " " not in w.strip()}

CODING = clean(CODING)
HACKING = clean(HACKING)
STRUCTURE = clean(STRUCTURE)
SLANG = clean(SLANG)
ATTITUDE = clean(ATTITUDE)
HUMOR = clean(HUMOR)
PATTERN = clean(PATTERN)

PLUS10 = CODING | HACKING | STRUCTURE | SLANG | ATTITUDE | HUMOR
PLUS7 = PATTERN - PLUS10


def main():
    out = Path(__file__).parent / "special_plus10s.txt"
    lines = [
        "# Lloyd Category Dictionary — ONLY words with importance values",
        "# Words NOT in these categories have NO value (not listed).",
        "#",
        "# ∆word+10$∆ = coding | hacking | english-structure | slang | attitude | humor",
        "# ∆word+7$∆  = pattern-indicator / relational-connector words",
        "# $ = context amplifier (spread importance to nearby words)",
        "# Ranking: +numbers > 0 > -numbers",
        "# Overlaps between +10$ and +7$ categories receive +10$ preference.",
        "#",
    ]
    for w in sorted(PLUS10):
        lines.append(f"∆{w}+10$∆")
    lines.append("")
    for w in sorted(PLUS7):
        lines.append(f"∆{w}+7$∆")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  +10$ words: {len(PLUS10)}")
    print(f"  +7$  words: {len(PLUS7)}")
    print(f"  total valued: {len(PLUS10) + len(PLUS7)}")
    print("  non-category words: 0 (no value)")
    print(f"  overlaps forced to +10$: {sorted(PATTERN & PLUS10)}")


if __name__ == "__main__":
    main()
