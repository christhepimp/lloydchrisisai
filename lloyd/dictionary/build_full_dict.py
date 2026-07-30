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
concurrency mutex lock semaphore deadlock racecondition atomic atomicity
go cplusplus csharp scala haskell elixir clojure erlang dart flutter reactnative
swiftui jetpack compose android ios macos windows
kubernetes k8s helm chart ingress service pod deployment statefulset
prometheus grafana elasticsearch kibana logstash fluentd
kafka rabbitmq redis mongodb postgresql mysql sqlite dynamodb cassandra
nginx apache tomcat gunicorn uvicorn
gitops argo flux jenkins travis circleci githubactions
terraform pulumi cloudformation ansible chef puppet
microservices eventdriven cqrs eventsourcing
solid dry kiss yagni cleanarchitecture hexagonal
monad functor applicative monoid semigroup
typeclass trait protocol interface
garbagecollector markandsweep referencecounting
jit aot interpreter bytecode
llvm clang gcc msvc rustc
package manager dependencyinjection inversionofcontrol
unit test integrationtest e2e endtoend
mock stub spy fixture
coverage branchcoverage linecoverage
profiler flamegraph memoryprofiler
async await coroutine greenlet
promise future task threadpool
websocket sse longpolling
restful soap rpc grpc
openapi swagger postman insomnia
jsonschema protobuf avro thrift
orm activerecord datamapper
migration seed fixture
index primarykey foreignkey constraint
transaction acid isolationlevel
normalization denormalization
sharding replication failover
loadbalancer reverseproxy cdn
cache invalidation ttl
ratelimit throttle circuitbreaker
retry backoff exponential
idempotent eventuallyconsistent
observability monitoring logging tracing
opentelemetry jaeger zipkin
featureflag canary bluegreen
rollback blue green deployment
infrastructure as code
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
pretexting sqlmap hydra medusa ncrack aircrackng reaver bully hashcat john mimikatz bloodhound
cobaltstrike empire metasploitframework wireshark tshark burpsuite owaspzap nessus openvas
nikto dirbuster gobuster sublist3r amass theharvester reconng maltego shodan censys
virustotal hybridanalysis cuckoo sandbox anyrun yara sigma snort suricata ossec wazuh
splunk elastic mitre attck tactics techniques procedures initialaccess execution persistence
privilegeescalation defenseevasion credentialaccess discovery lateralmovement collection
commandandcontrol exfiltration impact livingofftheland lolbins powershell empire
cobaltstrike redteam blueteam purpleteam threathunting incidentresponse forensics
memoryforensics volatility rekall autopsy sleuthkit
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
furthermore moreover nevertheless however despite whereas although though eventhough
inaddition additionally ontheotherhand forexample forinstance inotherwords thatis
asaresult asaconsequence dueto owingto inspiteof bymeansof inorderto sothat suchthat
notonly butalso eitheror neithernor bothand whetheror asif asthough ratherthan insteadof
accordingto withregardto intermsof onbehalfof infavorof incaseof bythetime assoon as
aslongas providedthat assumingthat giventhat seeingthat nowthat once whenever wherever
whatever whichever whoever whomever
""".split())

SLANG = set("""
yo sup bruh bro dude homie fam squad lit fire bussin cap nocap fr frfr ong bet
lowkey highkey sus salty mid slay slaps vibe vibes rizz sigma skibidi gyatt based cringe ratio
goat goated npc cope seethe aura drip flex clout stan tea spill periodt snatched lmao lmfao
lol rofl omg wtf smh fyp irl dm ghost ghosted simp simping thirsty downbad valid delulu
unalive iykyk rn nvm deadass finna gonna wanna gotta yall sis queen king bestie bff bae woke
trash cooked brainrot nocap forreal rizzler rizzgod delulu brainrot ratioed
itsgiving ate leftnocrumbs understoodtheassignment maincharacter sidecharacter
pookie baddie ick redflag greenflag situationship situationships ghosting breadcrumbing
orbiting softlaunch hardlaunch cuffingseason touchgrass nothoughts headempty livingrentfree
caughtin4k saidwhatneededtobesaid periodt slayqueen youatethat leftnocrumbs
understoodtheassignment maincharacterenergy sidecharacterenergy deluluisthesolulu
itsgiving notthe theaudacity thenerve icanteven imdeceased imdead imscreaming
imcrying imhowling imwheezing nocap cap mid trash cooked burnt fired slaps hitsdifferent
vibecheck auracheck rizzcheck sigmagrindset alpha beta omega npcbehavior maincharactersyndrome
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
confident selfconfident selfassured selfaware selfreliant selfsufficient ambitious driven
motivated determined persistent resilient tenacious gritty bold daring courageous fearless
fierce intense passionate enthusiastic optimistic pessimistic positive negative realistic
idealistic pragmatic cynical skeptical trusting openminded closedminded curious inquisitive
creative innovative analytical logical emotional rational empathetic compassionate kind cruel
generous selfish humble arrogant modest boastful honest dishonest loyal disloyal reliable
unreliable responsible irresponsible disciplined undisciplined focused distracted productive
lazy organized disorganized punctual late professional unprofessional mature immature wise
foolish intelligent stupid clever dumb witty dry sarcastic sincere blunt diplomatic direct
indirect assertive passiveaggressive dominant submissive leader follower independent dependent
stubborn flexible proud humble egodriven charismatic magnetic charming awkward stylish
fashionable edgy mainstream dark light toxic healthy genuine fake authentic performative
extra dramatic calm petty generous messy clean focused scattered disciplined wild
""".split())

HUMOR = set("""
joke jokes funny hilarious comedy comedian humor laugh laughing pun puns sarcasm
ironic irony satire parody meme memes shitpost troll trolling roast roasted burn gallows
morbid twisted sick disturbing offensive crude adult nsfw dirty raunchy sexual innuendo
punchline setup sketch improv wit corny cheesy unfunny deadpan absurdist surreal wholesome
cursed blessed chaos goblin feral unhinged deranged psychotic maniac evil villain spoiler
banter tease teasing dadjoke punny wordplay memeable shitposting darkcomedy blackcomedy standup
humorous comedic laughable ridiculous absurd surreal ironic sarcastic satirical parody
memeculture shitpostenergy trollbehavior roastsession burn gallowshumor darkhumor blackcomedy
morbidhumor twistedhumor sickjoke offensivehumor crudehumor adulthumor nsfwhumor dirtyjoke
raunchyjoke sexualhumor innuendo punchline setup sketchcomedy improvcomedy standup wittybanter
cornyjoke cheesyhumor unfunny deadpanhumor absurdisthumor surrealhumor wholesomememe cursedmeme
blessedmeme chaosenergy goblinmode feralmode unhingedenergy derangedtake psychoticbreak
maniacenergy evillaugh villainarc spoileralert banter teasing dadjoke pun wordplay
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
furthermore moreover nevertheless however despite whereas although though
inaddition additionally ontheotherhand forexample forinstance inotherwords thatis
asaresult dueto owingto inspiteof bymeansof inorderto sothat suchthat
notonly butalso eitheror neithernor bothand whetheror asif asthough ratherthan insteadof
accordingto withregardto intermsof onbehalfof infavorof incaseof bythetime assoon as
aslongas providedthat assumingthat giventhat seeingthat nowthat once whenever wherever
whatever whichever whoever whomever henceforth thereafter thereupon whereby wherein whereupon
albeit notwithstanding
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
