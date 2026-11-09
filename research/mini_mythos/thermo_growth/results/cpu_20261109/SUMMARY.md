# Growth by surprise while reading books (CPU)

Differences are model minus native Parcae (nats per token): negative = better. 'Read so far' is the
own-book tail windows (never read) of the books already read; 'held-out books' are books never read,
prepared like the read ones; 'Stage 1 books' are the hard-wrapped Stage 1 windows; c4 / wikitext /
fineweb show whether the rest of what Parcae knows stays intact.

| run | mode | directions k | prequential gain (all / 2nd half) | read-so-far tails | held-out books | Stage 1 books (hard-wrapped) | c4 | wikitext | fineweb |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| A_frozen_plain | auto | 40 | +0.1520 / +0.1660 | -0.1660 | -0.0722 | -0.0099 | +0.2826 | +0.2452 | +0.2648 |
| B_frozen_protected | auto | 34 | +0.1110 / +0.1131 | -0.1364 | -0.1044 | -0.0475 | +0.0252 | +0.0211 | +0.0302 |
| C_unfrozen_protected | auto + unfrozen | 39 | +0.1722 / +0.1822 | -0.2142 | -0.1491 | -0.0604 | +0.0669 | +0.0945 | +0.0727 |
| C_unfrozen_anchor3 | auto + unfrozen | 37 | +0.1237 / +0.1219 | -0.1733 | -0.1326 | -0.0642 | +0.0186 | +0.0357 | +0.0219 |
| C_unfrozen_anchor5 | auto + unfrozen | 37 | +0.1004 / +0.0996 | +0.0048 | -0.1167 | -0.0597 | +0.0096 | +0.0217 | +0.0105 |

Prequential gain = native loss minus the model's loss on each chunk BEFORE it learned from it
(positive = it predicts new text better than native).

Forgetting:

| run | anchor | crystallize | general text (c4/wiki/fineweb) | books: gain right after | at the end | lost | kept |
|---|---:|---:|---:|---:|---:|---:|---:|
| A_frozen_plain | 0.0 | 0 | +0.2642 (+30.2% ppl) | -0.1796 | -0.1660 | +0.0135 | 94% |
| B_frozen_protected | 1.0 | 12 | +0.0255 (+2.6% ppl) | -0.1257 | -0.1364 | -0.0107 | 110% |
| C_unfrozen_protected | 1.0 | 12 | +0.0780 (+8.1% ppl) | -0.2005 | -0.2142 | -0.0138 | 106% |
| C_unfrozen_anchor3 | 3.0 | 12 | +0.0254 (+2.6% ppl) | -0.1514 | -0.1733 | -0.0218 | 121% |
| C_unfrozen_anchor5 | 5.0 | 12 | +0.0139 (+1.4% ppl) | -0.1255 | +0.0048 | +0.1304 | -163% |

## A_frozen_plain: checks while reading

| books read | k | read-so-far tails | unread tails | held-out books | Stage 1 books | c4 | wikitext | fineweb |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | - | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| 5 | 10 | -0.1668 | -0.1271 | -0.0989 | -0.0301 | +0.0519 | +0.0369 | +0.0530 |
| 10 | 22 | -0.1752 | -0.1586 | -0.1233 | -0.0436 | +0.0987 | +0.0889 | +0.1066 |
| 15 | 29 | -0.1789 | -0.1851 | -0.1243 | -0.0439 | +0.1629 | +0.1413 | +0.1711 |
| 20 | 40 | -0.1660 | - | -0.0722 | -0.0099 | +0.2826 | +0.2452 | +0.2648 |

Directions as they grew (page, book, structure/noise vs temperature, tokens behind the pull):

- #1 page 0, book 0: 16.88 vs T 2.00 - '\n' '\n' '\n' '\n' '\n' ' nobody' '\n' '\n' 'w' '\n'
- #2 page 1, book 0: 7.68 vs T 1.90 - ' in' '\n' ' that' '\n' ' of' '\n' '\n' '\n' '\n' ' and'
- #3 page 2, book 0: 2.34 vs T 1.80 - '\n' '\n' '\n' '\n' '\n' '\n' '\n' '\n' '\n' '\n'
- #4 page 4, book 1: 1.75 vs T 1.63 - 'j' ' Durham' ' the' ' alone' ' Wyoming' ' not' ' quality' ' himself' ' neighbor' '\n'
- #5 page 6, book 2: 3.50 vs T 1.47 - 'ack' 'Well' 'ack' ' out' ' likely' ' anybody' ' out' ' by' ' out' ' out'
- #6 page 8, book 2: 2.40 vs T 1.33 - 'heads' 'wy' '\n' 'wy' 'I' "'d" ' dat' '\n' ' h' 'wy'
- #7 page 9, book 3: 4.40 vs T 1.26 - ' life' ' immun' 'withstanding' ' Magn' ' property' ' colleges' ' immun' ' Chart' 'withstanding' ' condem'
- #8 page 11, book 3: 1.77 vs T 1.14 - 'en' 'aving' ' worship' ' light' ' yet' 'ess' '."\n' ' never' ' settlement' ' retros'
- #9 page 12, book 4: 1.59 vs T 1.08 - '.' 'um' '-me' ' room' ' even' ' Rol' ' Uncle' ' times' ' even' 'ys'
- #10 page 14, book 4: 1.41 vs T 1.00 - 'agen' ' redd' ' myself' ' fitted' ' capt' 'CH' ' gentle' '."\n' 'My' ' occupied'
- #11 page 15, book 5: 1.88 vs T 1.00 - ' whom' ' Gly' 'rice' ' prize' ' Is' ' Is' ' Is' ' whom' 'abel' ' Gly'
- #12 page 16, book 5: 1.34 vs T 1.00 - ' I' ' pits' 'sy' 'enta' ' grace' ' morning' 'iable' 'osp' ' courtesy' ' morning'
- #13 page 17, book 5: 1.03 vs T 1.00 - 'u' ' and' 'ents' ',"' ' word' ' un' ' chance' ' impression' ' by' 'ic'
- #14 page 18, book 6: 1.30 vs T 1.00 - 'ment' ' on' 'ly' ' people' ' me' ' Mons' ' understood' 't' ' attending' 's'
- #15 page 19, book 6: 1.19 vs T 1.00 - 'fully' 'is' ' de' ' de' ' de' ' antip' ';' ' name' ' prof' ' was'
- #16 page 21, book 7: 2.09 vs T 1.00 - ' Bud' 'in' ' Bud' ' Bud' 'erer' ' Bud' ' out' '!"' ' Dick' ' Bud'
- #17 page 23, book 7: 1.27 vs T 1.00 - ' s' ' excuse' ' st' ' consent' 'ily' ' "' 'rusted' ' bar' ' fore' ' d'
- #18 page 24, book 8: 1.12 vs T 1.00 - ' fore' ' walls' '-' 'ving' ' perch' 'se' 'ness' 'ending' ' my' 'ote'
- #19 page 25, book 8: 1.02 vs T 1.00 - 't' ' conceal' 'ign' ' amuse' ' cave' ' himself' ' Barn' ' quiet' ' last' ' himself'
- #20 page 26, book 8: 1.01 vs T 1.00 - 'ton' 'orses' 'ton' ' Lo' ' inherit' ' hall' ' beauty' 'har' ' char' 'vell'
- #21 page 27, book 9: 1.63 vs T 1.00 - 'ied' 'el' ' pleasure' 'ity' 'ans' 'ers' 'ity' 'el' ' Hans' 'inker'
- #22 page 29, book 9: 1.20 vs T 1.00 - ' inward' 'cha' ' Cats' ' down' ' TH' ' eng' 'us' ' kiss' ' air' ' bundles'
- #23 page 30, book 10: 1.25 vs T 1.00 - ' no' ' no' 'a' '"I' ' Fork' ' locked' ' no' ' des' '-k' ' eyes'
- #24 page 31, book 10: 1.24 vs T 1.00 - ' and' ' choose' '?"\n' ' up' ' chosen' ' Cleveland' ' lim' '?"\n' ' favour' ' place'
- #25 page 36, book 12: 1.52 vs T 1.00 - 'forth' 'the' 'd' 'oker' ' sleep' ' precious' ' Ste' ' tr' ' want' 'forth'
- #26 page 37, book 12: 1.18 vs T 1.00 - "'T" ' House' ' my' ' I' ' tears' ' my' ' ex' ' Ste' ' I' ' my'
- #27 page 40, book 13: 1.03 vs T 1.00 - 'one' ' Mrs' 'add' ' her' 'old' 'ity' ' her' ' her' ' her' ' her'
- #28 page 42, book 14: 1.13 vs T 1.00 - 'ful' ' media' 'ce' 'or' 'red' ' which' ' Dar' ' Bacon' ' Fair' ' reserved'
- #29 page 44, book 14: 1.05 vs T 1.00 - 'eding' ' occupied' ' everywhere' ' window' ' burning' 'ion' 'Thus' ' observers' ' spr' ' mean'
- #30 page 45, book 15: 1.52 vs T 1.00 - 'ioned' ' black' 'ight' ' theirs' ' loss' ' her' 'ny' ' noise' '-n' ' G'
- #31 page 46, book 15: 1.28 vs T 1.00 - ' silk' ' servants' ' extremities' ' when' ' before' ' he' 'ake' ' when' ' a' 'oom'
- #32 page 47, book 15: 1.11 vs T 1.00 - ' She' 'ion' ' gar' "'s" ' him' 'ols' ' ps' ' prisoner' ' Lock' ','
- #33 page 48, book 16: 2.65 vs T 1.00 - ' and' 'ce' ' beverage' 'ce' ' cul' 'III' ' function' ' ceremony' ' Philos' 'ard'
- #34 page 50, book 16: 1.42 vs T 1.00 - 'ine' 'm' 'ist' ' refine' ' Z' ' tok' ' time' ' useless' ' vulgar' ' interior'
- #35 page 51, book 17: 1.20 vs T 1.00 - 'p' 'y' 'day' ' leather' ' Johns' 'y' 'ign' ' of' ' us' ' of'
- #36 page 54, book 18: 1.13 vs T 1.00 - ' Eg' 'head' 'ge' 'de' ' Frank' ' Eg' "'s" ' Eg' ' chance' 'R'
- #37 page 55, book 18: 1.04 vs T 1.00 - ' exercise' ' h' " '" ' implanted' ' blow' 'cels' ' why' ',' ' itself' ' than'
- #38 page 56, book 18: 1.01 vs T 1.00 - 'erv' 'vel' ' he' 'it' ' ways' ' children' ' he' ".'" 'HER' 'ne'
- #39 page 57, book 19: 1.24 vs T 1.00 - 'a' ' malf' 'chief' ' fore' 'uff' ' War' ' refuge' ' p' ' War' 'hed'
- #40 page 58, book 19: 1.01 vs T 1.00 - ' accord' ' Hast' ' Hast' ' Hast' ' Hast' ' Hast' ' Hast' ' acted' ' assigned' ' assigned'

## B_frozen_protected: checks while reading

| books read | k | read-so-far tails | unread tails | held-out books | Stage 1 books | c4 | wikitext | fineweb |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | - | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| 5 | 11 | -0.1544 | -0.1075 | -0.0905 | -0.0386 | +0.0209 | +0.0147 | +0.0194 |
| 10 | 20 | -0.1326 | -0.1047 | -0.0981 | -0.0416 | +0.0175 | +0.0155 | +0.0185 |
| 15 | 27 | -0.1341 | -0.1234 | -0.1026 | -0.0520 | +0.0161 | +0.0147 | +0.0172 |
| 20 | 34 | -0.1364 | - | -0.1044 | -0.0475 | +0.0252 | +0.0211 | +0.0302 |

Directions as they grew (page, book, structure/noise vs temperature, tokens behind the pull):

- #1 page 0, book 0: 16.88 vs T 2.00 - '\n' '\n' '\n' '\n' '\n' ' nobody' '\n' '\n' 'w' '\n'
- #2 page 1, book 0: 7.13 vs T 1.90 - ' in' '\n' ' that' '\n' ' of' '\n' '\n' '\n' '\n' '\n'
- #3 page 3, book 1: 2.31 vs T 1.71 - ' guards' ' compass' ' vice' ' L' ' east' 'ish' 'ant' ' strange' ' residence' ' long'
- #4 page 5, book 1: 1.77 vs T 1.55 - ' rest' ' direction' ' animal' ' country' ' himself' ' canon' ' missed' ' west' ' road' ' unm'
- #5 page 6, book 2: 3.14 vs T 1.47 - ' anybody' 'ack' 'ack' ' up' '\xa0' ' out' ' likely' 'Well' ' twelve' ' matches'
- #6 page 7, book 2: 1.78 vs T 1.40 - ' sleep' ' breath' 'aked' ' couldn' ' right' ' man' 'gg' ' year' ' nothing' ' man'
- #7 page 8, book 2: 2.48 vs T 1.33 - 'heads' '\xa0' "'d" '\n' ' to' ' to' ' er' 'wy' '\xa0' ' stuck'
- #8 page 9, book 3: 3.54 vs T 1.26 - ' life' ' property' 'withstanding' ' immun' 'withstanding' ' Magn' ' acts' ' the' ' colleges' ' judges'
- #9 page 11, book 3: 1.81 vs T 1.14 - 'en' ' light' ' conting' ' settlement' ' yet' ' reclaim' '!' 'rec' 'ess' ' worship'
- #10 page 12, book 4: 1.43 vs T 1.08 - ' room' ' Uncle' '.' 'um' ' Uncle' ' Uncle' ' Captain' ' Rol' ' eye' 'CH'
- #11 page 13, book 4: 1.10 vs T 1.03 - ' ourselves' ' Ca' ' him' 'and' 'es' 'more' 'ci' ',' ' vain' 'der'
- #12 page 15, book 5: 1.64 vs T 1.00 - ' whom' ' prize' ' Gly' ' ut' ' fate' ' more' ' whom' 'Is' ' that' ' of'
- #13 page 17, book 5: 1.38 vs T 1.00 - ' there' ' and' ' impression' ' un' '?"\n' '?"\n' 'ic' ' day' 'u' ' day'
- #14 page 18, book 6: 1.11 vs T 1.00 - 't' ' "' 'ment' ' actions' 'use' 'ly' 't' ' "' 't' 'ates'
- #15 page 19, book 6: 1.04 vs T 1.00 - ' name' ' de' '!"\n' ' de' ' escape' '."\n' ' antip' ' de' 'bour' ',"'
- #16 page 21, book 7: 1.64 vs T 1.00 - 'in' ' pocket' ' Bud' ' Bud' 'CH' 'erer' ' Bud' ' out' ' matter' ' Bud'
- #17 page 23, book 7: 1.11 vs T 1.00 - ' s' ' ' ' ' 'iest' 'iven' ' st' ' excuse' 'ily' 'rusted' ' Top'
- #18 page 24, book 8: 1.22 vs T 1.00 - 'se' 'ote' 'ibly' 'ving' ' perch' 'iner' ' Se' ' walls' ' ring' ' my'
- #19 page 27, book 9: 1.46 vs T 1.00 - 'ied' 'el' 'ack' ' American' 'ra' 'ity' 'ans' ' stock' 'ity' ','
- #20 page 29, book 9: 1.07 vs T 1.00 - ' G' 'us' ' states' ' air' ' TH' ' eng' ' Cats' 'e' ' bundles' ' children'
- #21 page 30, book 10: 1.19 vs T 1.00 - ' rob' ' locked' ' magist' ' no' '-' 's' "'t" ' grab' 'so' ' des'
- #22 page 32, book 10: 1.30 vs T 1.00 - 'ased' 'ok' 'ress' ' count' ' volumes' ' in' '.\n' 'pe' ' count' ' aston'
- #23 page 36, book 12: 1.17 vs T 1.00 - 'the' 'forth' 'forth' ' tr' ' Sche' ' flavour' 'est' 'I' 'ushed' 'I'
- #24 page 37, book 12: 1.20 vs T 1.00 - ' House' ' tears' "'T" ' whom' 'ommy' ' Ste' ' Ste' ' Ste' ' Ste' ' tears'
- #25 page 39, book 13: 1.32 vs T 1.00 - ' patience' ' waiting' ' line' ' policy' 'rig' ' few' ' paper' ' accompan' '.\n' ' line'
- #26 page 42, book 14: 1.43 vs T 1.00 - 'red' ' media' '-cl' ' true' ' Mr' ' at' ' Sir' '-' ' beside' ' colour'
- #27 page 44, book 14: 1.00 vs T 1.00 - ' explosion' 'eding' 'ull' ' window' ' rec' ' everywhere' ' this' 'one' 'ither' ' here'
- #28 page 45, book 15: 1.18 vs T 1.00 - 'ioned' ' black' ' her' ' her' ' her' ' her' 's' ' her' ' ro' ' she'
- #29 page 46, book 15: 1.34 vs T 1.00 - ' silk' ' dam' ' servants' ' Ellen' ' garments' 'light' ' before' ' when' ' discom' ' fro'
- #30 page 48, book 16: 2.81 vs T 1.00 - ' and' 'ce' ' the' 'III' 'ce' ' priesthood' ' name' ' function' ' beverage' ' Te'
- #31 page 50, book 16: 1.51 vs T 1.00 - 'ist' 'ine' ' tok' ' Z' ' tok' ' extreme' ' but' ' Z' ' possible' ' melody'
- #32 page 55, book 18: 1.16 vs T 1.00 - ' implanted' 'hip' 'cels' " '" ' Ah' ' Poverty' '?' ' and' '?' ' h'
- #33 page 57, book 19: 1.11 vs T 1.00 - ' malf' ' refuge' ' bra' 'ess' ' fore' ' myself' 'uff' 'a' 'arm' 'ber'
- #34 page 58, book 19: 1.00 vs T 1.00 - ' accord' ' Hast' ' Hast' ' Hast' ' Hast' ' Hast' ' hast' ' Hast' ' acted' ' '

## C_unfrozen_protected: checks while reading

| books read | k | read-so-far tails | unread tails | held-out books | Stage 1 books | c4 | wikitext | fineweb |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | - | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| 5 | 10 | -0.1895 | -0.1421 | -0.1153 | -0.0572 | +0.0341 | +0.0345 | +0.0388 |
| 10 | 20 | -0.1892 | -0.1748 | -0.1395 | -0.0677 | +0.0439 | +0.0601 | +0.0476 |
| 15 | 27 | -0.2045 | -0.2059 | -0.1475 | -0.0663 | +0.0559 | +0.0663 | +0.0590 |
| 20 | 39 | -0.2142 | - | -0.1491 | -0.0604 | +0.0669 | +0.0945 | +0.0727 |

Directions as they grew (page, book, structure/noise vs temperature, tokens behind the pull):

- #1 page 0, book 0: 13.70 vs T 2.00 - 'G' ' nobody' '\n' '\n' '\n' 'w' '\n' 'alf' '\n' '\n'
- #2 page 2, book 0: 2.47 vs T 1.80 - 'ness' ' succeeding' 'rets' 'ractical' 'oda' 'ce' 'es' 'ble' 'rast' 'ness'
- #3 page 3, book 1: 1.74 vs T 1.71 - ' compass' 'ant' 'ish' ' guards' ' L' ' stranger' ' strange' ' boy' ' pasture' ' arous'
- #4 page 6, book 2: 2.23 vs T 1.47 - ' back' ' Any' ' up' 'ed' ' I' ' anybody' '\n' 'ack' ' up' ' By'
- #5 page 7, book 2: 1.82 vs T 1.40 - ' sleep' ' dark' ' next' ' amongst' ' further' ' breath' ' I' ' last' ' breakfast' 'I'
- #6 page 8, book 2: 2.33 vs T 1.33 - 'J' '\xa0' 'heads' "'d" '\n' '\xa0' '\n' ' to' ' to' ' in'
- #7 page 9, book 3: 2.80 vs T 1.26 - ' life' ' Magn' ' property' ',' ' the' ' immun' 'withstanding' ' and' ' acts' ' Jud'
- #8 page 11, book 3: 1.83 vs T 1.14 - ' fathers' ' reclaim' 'or' ' yet' 'en' ' Mar' ' full' ' form' ' by' ' yet'
- #9 page 12, book 4: 1.72 vs T 1.08 - '.' ' Uncle' ' pap' ' Mr' '.' '?"\n' 'out' ' and' ' Uncle' ' Rol'
- #10 page 13, book 4: 1.27 vs T 1.03 - ' ourselves' 'ci' 'der' 'able' ' for' 'nder' ' Ca' 'apes' ' vain' ' first'
- #11 page 15, book 5: 1.83 vs T 1.00 - ' whom' ' morning' ' Gly' ' from' ' whom' 'abel' ' in' 'Is' ' prize' 'y'
- #12 page 18, book 6: 1.02 vs T 1.00 - ' me' 'CH' ' honour' ' people' ' memoir' 'ment' ' attending' ' aph' ' reflections' ' human'
- #13 page 19, book 6: 1.18 vs T 1.00 - 'bour' '!"\n' ' name' ' few' '."\n' 'ata' ' moment' 'rait' '?"\n' '."\n'
- #14 page 21, book 7: 2.22 vs T 1.00 - ' Bud' ' Bud' ' Lane' ' out' ' Lane' ' Bud' ' soul' ' Lane' 'in' ' Lane'
- #15 page 22, book 7: 1.01 vs T 1.00 - ' dim' ' Bud' ' Bud' ' idea' ' Together' ' future' ' Bud' ' Bud' ' Bud' ' anything'
- #16 page 23, book 7: 1.01 vs T 1.00 - ' "' ' s' ' Mrs' ' excuse' ' "' ' bar' ' "' 'Then' 'ol' ' air'
- #17 page 24, book 8: 1.53 vs T 1.00 - 'ote' 'se' ' fore' 'ending' ' ourselves' ' us' ' school' ' with' ' my' ' my'
- #18 page 26, book 8: 1.15 vs T 1.00 - 'har' '?"\n' ' Lo' '?"\n' '!"\n' ' char' 'ton' 'orses' '?"\n' 'de'
- #19 page 27, book 9: 2.06 vs T 1.00 - 'ied' ' American' 'ra' 'ons' 'ans' 'uild' ' sk' '.' ' we' ' snow'
- #20 page 29, book 9: 1.14 vs T 1.00 - ' Cats' ' arrows' ' inward' ' Cats' 'cha' ' and' ' and' ' Ven' ' kiss' ' air'
- #21 page 30, book 10: 1.19 vs T 1.00 - ' mad' 'ic' ' None' ' eyes' ' eyes' ' always' 'ice' ' Fork' 'rup' ' gone'
- #22 page 36, book 12: 1.28 vs T 1.00 - 'the' 'forth' "'" ' qu' "'" 'forth' ' nor' "'" 'd' ' kept'
- #23 page 37, book 12: 1.21 vs T 1.00 - ' myself' ' Ste' ' tears' ' whom' ' Ste' ' House' ' I' 'd' ' Ste' ' Ste'
- #24 page 38, book 12: 1.06 vs T 1.00 - ' "' 'ily' ' to' ' to' ' to' ' to' ' taking' ' Pe' ' "' ' if'
- #25 page 39, book 13: 1.37 vs T 1.00 - ' I' ' vain' ' dissatis' ' to' ' waiting' ',' ' seldom' '-time' ' rolling' ' my'
- #26 page 42, book 14: 1.22 vs T 1.00 - ' at' ' Dar' ' former' 'igma' 'ley' ' Ant' 'ven' ' career' ' wander' ' Lion'
- #27 page 44, book 14: 1.14 vs T 1.00 - ' spr' ' window' 'y' ' spr' ' observers' ' even' 'bing' ' Lion' ' here' ' upon'
- #28 page 45, book 15: 1.40 vs T 1.00 - ' theirs' 'ioned' ' heaven' ' to' ' heaven' ' in' 's' ' little' ' heart' ' midnight'
- #29 page 46, book 15: 1.31 vs T 1.00 - ' silk' ' dam' ' servants' ' fl' ' extremities' ' clothes' 'claim' 'athy' ' Ear' ' Mr'
- #30 page 48, book 16: 4.11 vs T 1.00 - ' movement' ' and' ' the' 'se' ' beverage' 'III' ' hundred' ' "' ' were' 'ce'
- #31 page 50, book 16: 1.27 vs T 1.00 - ' and' 'ism' ' equal' ' and' ' differs' 'ism' ' tok' ' mant' ' resp' ' tok'
- #32 page 51, book 17: 1.58 vs T 1.00 - ',' 'y' ' lady' ',' ',' 'y' ',' ',' ',' ' Lady'
- #33 page 52, book 17: 1.05 vs T 1.00 - 'ingly' '-makers' ' written' "'\n" ' chess' 'ress' '."' ' was' 'urt' ' div'
- #34 page 53, book 17: 1.00 vs T 1.00 - 'arer' 'nel' '!"\n' '."\n' '."\n' '?' '."\n' ' read' 'ed' ' Childhood'
- #35 page 54, book 18: 1.12 vs T 1.00 - ' Frank' ' abruptly' 'head' ' heir' ' Haz' ' heir' ' p' 'ided' 'andal' '-'
- #36 page 55, book 18: 1.19 vs T 1.00 - ' Ah' ' implanted' ' Mamm' ' that' 'iest' '?' ' bre' ' that' 'e' ' why'
- #37 page 56, book 18: 1.03 vs T 1.00 - 'ius' '?"\n' ' Zen' 'ius' '?"\n' ".'" ' it' ' it' '!"\n' ' Directory'
- #38 page 57, book 19: 1.28 vs T 1.00 - 'craft' 'let' ' malf' 'a' ' rack' ' me' ' family' 'eck' ' visitor' ' refuge'
- #39 page 58, book 19: 1.00 vs T 1.00 - 'iest' ' g' 'elcome' 'ple' 'ly' 'ner' ' w' 'rets' ' means' ' w'

Relative change of Parcae's own weights: C 0.0003, adapter 0.0002, coda 0.0027, core_block 0.0034, ln_f 0.0008, ln_prelude 0.0033, prelude 0.0036, value_embeds 0.0000, wte 0.0007

## C_unfrozen_anchor3: checks while reading

| books read | k | read-so-far tails | unread tails | held-out books | Stage 1 books | c4 | wikitext | fineweb |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | - | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| 5 | 10 | -0.1382 | -0.1133 | -0.0943 | -0.0537 | +0.0114 | +0.0115 | +0.0123 |
| 10 | 18 | -0.1482 | -0.1334 | -0.1181 | -0.0613 | +0.0129 | +0.0211 | +0.0136 |
| 15 | 25 | -0.1579 | -0.1569 | -0.1213 | -0.0654 | +0.0178 | +0.0271 | +0.0198 |
| 20 | 37 | -0.1733 | - | -0.1326 | -0.0642 | +0.0186 | +0.0357 | +0.0219 |

Directions as they grew (page, book, structure/noise vs temperature, tokens behind the pull):

- #1 page 0, book 0: 10.82 vs T 2.00 - 'G' ' nobody' 'w' '\n' 'alf' '\n' 'zen' '--' '\n' '\n'
- #2 page 1, book 0: 2.10 vs T 1.90 - '\n' ' of' 'eness' '\n' 'tt' '\n' 'ness' '\n' '\n' '\n'
- #3 page 5, book 1: 1.86 vs T 1.55 - ' inmates' ' road' 'ulph' ' animal' ' direction' ' they' ' their' '\n' ' they' ' himself'
- #4 page 6, book 2: 2.49 vs T 1.47 - ' anybody' ' up' ' I' ' something' 'ack' ' wood' 'ky' ' up' ' sell' 'Well'
- #5 page 7, book 2: 1.72 vs T 1.40 - ' amongst' ' couldn' ' plenty' 'ety' ' time' 'Well' ' ' ' amongst' ' woods' 'So'
- #6 page 8, book 2: 2.15 vs T 1.33 - 'J' 'I' 'heads' ' in' '\n' '\n' '\xa0' ' in' '\n' '\xa0'
- #7 page 9, book 3: 2.72 vs T 1.26 - ' life' 'withstanding' ' Magn' ' property' ' Hampshire' ' surrend' ' visitors' ' free' ',' ' the'
- #8 page 12, book 4: 1.86 vs T 1.08 - '-me' '.' ' same' ' Uncle' ' Mr' ' Uncle' '.' ' same' ' Rol' ' clever'
- #9 page 13, book 4: 1.36 vs T 1.03 - ' ourselves' 'and' 'der' ' Uncle' 'more' 'apes' ' for' ' vain' ' inc' 'able'
- #10 page 14, book 4: 1.04 vs T 1.00 - 'in' 'in' ' Dame' "'S" ' Hast' '"A' 'ly' 'his' ' rank' ' or'
- #11 page 15, book 5: 1.96 vs T 1.00 - 'abel' 'ep' ' whom' ' Is' ' arr' ' Is' ' whom' ' from' 'as' 'rice'
- #12 page 16, book 5: 1.04 vs T 1.00 - 'erv' 'ta' ' herself' ' grace' ' day' ' I' ' silence' 'osp' ' English' ' English'
- #13 page 17, book 5: 1.03 vs T 1.00 - 't' ' places' ' and' 'ic' ' there' ' alone' 'theless' 'arted' 'lessly' ' gro'
- #14 page 19, book 6: 1.27 vs T 1.00 - 'bour' ';' '!"\n' 'is' '."\n' '."\n' 'hes' '?"\n' 'ness' 'rait'
- #15 page 21, book 7: 1.81 vs T 1.00 - ' Bud' ' Territory' ' Bud' ':\n' 'ee' ' lone' ' pocket' ' Bud' ' Bud' ' though'
- #16 page 24, book 8: 1.52 vs T 1.00 - ' ourselves' 'se' 'peak' 'ote' 'ving' ' Heaven' ' cliffs' 'ated' ' "' ' school'
- #17 page 26, book 8: 1.06 vs T 1.00 - ' Lo' ' Count' 'ship' 'ton' ' Count' 'de' ' cheek' ' spleen' 'orses' ' despair'
- #18 page 27, book 9: 1.87 vs T 1.00 - 'el' ' that' 'ons' ',' ' American' 'iful' ' Do' 'inker' ' Nicholas' ' We'
- #19 page 30, book 10: 1.15 vs T 1.00 - 'umbling' '"I' ' appeared' 'I' ' you' ' or' ' daughter' ' me' ' mad' ' eyes'
- #20 page 33, book 11: 1.02 vs T 1.00 - 'apes' ' fur' ' spr' ' skin' ' handsome' ' calming' ' eyes' '.' ' Quick' 'oe'
- #21 page 36, book 12: 1.23 vs T 1.00 - 'oker' 'forth' 'the' 'les' "'" "'" 'les' 'forth' 'est' ' kept'
- #22 page 37, book 12: 1.19 vs T 1.00 - ' Ste' ' House' ' Ste' ' Ste' 'd' ' Ste' ' Ste' 'd' ' I' ' Ste'
- #23 page 38, book 12: 1.14 vs T 1.00 - 'in' ' if' ' to' ' taking' ' to' ' to' 'in' 'ara' ' to' ' to'
- #24 page 42, book 14: 1.46 vs T 1.00 - ' more' ' at' ' longevity' ' Sir' ' more' ' thee' ' Ant' ' fragments' ' Alt' ' more'
- #25 page 44, book 14: 1.01 vs T 1.00 - ' Lion' ' window' ' spr' ' spr' ' P' ' observers' ' he' ' H' ' distinction' ' P'
- #26 page 45, book 15: 1.25 vs T 1.00 - 'ioned' ' left' ' midnight' ' She' ' other' ' in' ' little' '-n' ' stepped' ' funeral'
- #27 page 46, book 15: 1.26 vs T 1.00 - ' matters' ' them' ' Mr' ' silk' ' clothes' ' beauty' ' young' ' second' ' Christmas' ' welcome'
- #28 page 48, book 16: 3.25 vs T 1.00 - ' the' ' movement' ' and' 'ce' 'III' ' Kw' 'road' ' priesthood' '.' ' "'
- #29 page 49, book 16: 1.27 vs T 1.00 - 'met' 'm' 'a' ' account' ' reflection' ' out' ' Zen' ' certainly' ' Su' ' play'
- #30 page 50, book 16: 1.16 vs T 1.00 - ' differs' ' stood' ' pictured' '.' ' walls' 'zed' ' even' 'aim' ',' ','
- #31 page 51, book 17: 1.25 vs T 1.00 - ' the' ' family' ',' '-M' ' Gr' ',' ' Lady' ' being' ',' 'p'
- #32 page 52, book 17: 1.02 vs T 1.00 - 'ingly' '-makers' "'\n" ' chess' 'aver' ' was' ' judgment' 'Char' '!"' '."\n'
- #33 page 53, book 17: 1.23 vs T 1.00 - 'arer' ',' '!"\n' ' and' ' matter' '?' ',' ' read' '."\n' '."\n'
- #34 page 55, book 18: 1.10 vs T 1.00 - 'hip' ' our' ' why' ' bre' ' God' ' that' ' God' ' alone' ' that' 'ation'
- #35 page 56, book 18: 1.04 vs T 1.00 - '?"\n' ".'" "?'" '?"\n' '!"\n' ' Zen' '-sh' ',' '."\n' ' Directory'
- #36 page 58, book 19: 1.11 vs T 1.00 - ' of' ' Inst' ' dam' ' imp' '--' ' accord' ' Hast' ' ' ' unw' ' S'
- #37 page 59, book 19: 1.06 vs T 1.00 - 'Richard' ' Right' 'orter' ' Adam' ' ever' ' recreation' ' Adam' 'Meanwhile' 'orter' ' Wit'

Relative change of Parcae's own weights: C 0.0003, adapter 0.0002, coda 0.0025, core_block 0.0031, ln_f 0.0007, ln_prelude 0.0030, prelude 0.0033, value_embeds 0.0000, wte 0.0006

## C_unfrozen_anchor5: checks while reading

| books read | k | read-so-far tails | unread tails | held-out books | Stage 1 books | c4 | wikitext | fineweb |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | - | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| 5 | 8 | -0.1281 | -0.0721 | -0.0844 | -0.0500 | +0.0066 | +0.0105 | +0.0058 |
| 10 | 17 | -0.1277 | +0.4991 | -0.1018 | -0.0547 | +0.0074 | +0.0160 | +0.0059 |
| 15 | 25 | -0.1371 | -0.1306 | -0.1080 | -0.0598 | +0.0100 | +0.0165 | +0.0108 |
| 20 | 37 | +0.0048 | - | -0.1167 | -0.0597 | +0.0096 | +0.0217 | +0.0105 |

Directions as they grew (page, book, structure/noise vs temperature, tokens behind the pull):

- #1 page 0, book 0: 8.28 vs T 2.00 - 'G' ' nobody' 'w' 'alf' '\n' ' too' '--' '\n' '\n' 'zen'
- #2 page 1, book 0: 2.67 vs T 1.90 - ' of' '\n' '\n' '\n' '\n' '\n' 'tt' '\n' 'abl' '\n'
- #3 page 6, book 2: 1.60 vs T 1.47 - ' up' ' anybody' 'Well' ' up' 'ack' ' up' ' something' ' you' 'ky' ' up'
- #4 page 7, book 2: 1.76 vs T 1.40 - ' amongst' ' ' 'So' ' on' ' time' 'ety' ' couldn' ' amongst' ' About' ' plenty'
- #5 page 8, book 2: 2.63 vs T 1.33 - 'J' 'I' 'heads' '\n' '\n' '\n' 'Well' '\n' '\n' '\n'
- #6 page 9, book 3: 2.47 vs T 1.26 - ' life' ' property' ' Magn' 'withstanding' ' living' ' Hampshire' 'ized' ' Hol' ' live' ' light'
- #7 page 12, book 4: 1.21 vs T 1.08 - '.' '.' '-me' ' same' ' same' ' pap' ' why' ' is' ' called' 'ash'
- #8 page 13, book 4: 1.24 vs T 1.03 - 'more' ' Uncle' ' inc' '-D' ' race' ' he' '"' ' Rol' ' and' ' he'
- #9 page 15, book 5: 1.67 vs T 1.00 - ' Is' 'as' 'ep' ' Is' ' whom' ' fate' ' whom' ' Is' 'age' 'uted'
- #10 page 16, book 5: 1.09 vs T 1.00 - ' herself' ' indeed' ' breeze' ' else' 'erv' ' English' ' pol' ' English' ' her' ' day'
- #11 page 19, book 6: 2.32 vs T 1.00 - ';' 'rait' 'bour' 'nt' "'s" ' passed' '."\n' ' than' ' honour' 'ly'
- #12 page 21, book 7: 1.75 vs T 1.00 - 'ee' ' Bud' ' Bud' ' the' ' Bud' ' Bud' ' in' 'ning' ' Hoover' 'ul'
- #13 page 22, book 7: 1.20 vs T 1.00 - ' Bud' ' Bud' ' Bud' ' Bud' ' Bud' ' Bud' ' dim' ' Bud' ' idea' ' Bud'
- #14 page 23, book 7: 1.19 vs T 1.00 - 'ed' ' Mrs' ' j' 'ests' 'red' 'no' ' trail' ' ceremony' ' Later' 'inded'
- #15 page 24, book 8: 1.42 vs T 1.00 - ' ourselves' 'se' ' perch' ' az' 'otional' ' Heaven' ' grie' ' our' 'ated' ' Heaven'
- #16 page 26, book 8: 1.25 vs T 1.00 - ' spleen' ' to' ' despair' 'room' ' beauty' ' four' '\n' 'id' ' four' ' cried'
- #17 page 27, book 9: 1.48 vs T 1.00 - 'ons' '{' 'el' '{' ' too' ' worth' ' we' ' G' ' trading' 'b'
- #18 page 32, book 10: 1.08 vs T 1.00 - ' part' 'ible' 'est' ' evil' 'F' ' g' 'ated' ' life' ' cold' ' Malt'
- #19 page 33, book 11: 1.09 vs T 1.00 - ' eyes' ' and' ' fur' 'el' ' faith' ' tones' ' re' ' Quick' 'apes' ' skin'
- #20 page 36, book 12: 1.32 vs T 1.00 - "'" "'" "'" 'oker' 'The' 'le' 'the' ' passage' 'I' 'ill'
- #21 page 37, book 12: 1.03 vs T 1.00 - ' I' ' I' ' at' ' House' ' I' ' I' 'erred' 'ommy' ' Ste' ' I'
- #22 page 39, book 13: 1.65 vs T 1.00 - ' vain' ' dissatis' ',' ' seldom' '-time' ' to' ' refused' ',' ' forcibly' ' ut'
- #23 page 42, book 14: 1.63 vs T 1.00 - '!"\n' '!"\n' ' Ant' ' longevity' ' amidst' '?"\n' '!"\n' ' Dar' ' thee' '!"\n'
- #24 page 43, book 14: 1.08 vs T 1.00 - 'agon' 'l' 'augh' 'augh' ' he' 'r' ' Ralph' ' slipped' 'r' ' he'
- #25 page 44, book 14: 1.01 vs T 1.00 - ' Lion' ' spr' ' spr' ' boy' 'ang' '."\n' 'rog' 'ers' ' P' '."\n'
- #26 page 45, book 15: 1.53 vs T 1.00 - 'ioned' ' place' 'eping' ' heaven' ' ro' ' heaven' ' heart' ' to' ' born' ' bright'
- #27 page 46, book 15: 1.30 vs T 1.00 - ' silk' 'tery' 'athy' '--' '--' 'urable' ' Mr' ' beauty' ' them' ' clothes'
- #28 page 48, book 16: 1.99 vs T 1.00 - ' the' 'esc' ' movement' ' priesthood' 'III' ' adequate' ' manual' ' places' '-g' ' word'
- #29 page 49, book 16: 1.30 vs T 1.00 - 'met' 'sy' 'm' ' Su' ' reflection' 'enn' ' weight' 'ist' ' Su' ' play'
- #30 page 50, book 16: 1.18 vs T 1.00 - 'ism' ' symmetry' '.' ' equal' ' stood' ' expression' ' dynamic' 'ism' ' resp' ' walls'
- #31 page 51, book 17: 1.02 vs T 1.00 - ' the' 'umbered' ',' ',' 'hol' ',' 'ly' ' family' 's' ' Gr'
- #32 page 53, book 17: 1.08 vs T 1.00 - '."\n' 'nel' 'arer' ',' '!"\n' 'e' '."\n' ',' ' and' '."\n'
- #33 page 54, book 18: 1.06 vs T 1.00 - ' return' 'ull' 'ontin' ' chance' 'ust' '\n' '\n' ' painter' ' sol' ' sol'
- #34 page 55, book 18: 1.39 vs T 1.00 - ' bre' 'hip' ' our' ' that' ' why' ' Poverty' ' mud' ' that' ' ease' ' ease'
- #35 page 56, book 18: 1.17 vs T 1.00 - ".'" '?"\n' '!"\n' 'erv' '?"\n' "?'" 'E' ',' ' Byz' ' sounding'
- #36 page 57, book 19: 1.31 vs T 1.00 - 'ir' ' visitor' ' life' ' me' ' Lancaster' ',' ' whom' 'oes' ' br' 'ais'
- #37 page 59, book 19: 1.14 vs T 1.00 - ' Right' 'Richard' ',' ' Adam' ' ever' ' ' ' prisoner' ' recreation' 'vell' 'orter'

Relative change of Parcae's own weights: C 0.0003, adapter 0.0002, coda 0.0024, core_block 0.0029, ln_f 0.0007, ln_prelude 0.0027, prelude 0.0031, value_embeds 0.0000, wte 0.0006


## Stability (stability_scan.py, final models, 160 check windows each)

| run | blow-ups (NLL diff > 0.5) | largest hidden-norm ratio vs native | worst window |
|---|---:|---:|---:|
| A_frozen_plain | 0 | 1.38 | +0.48 |
| B_frozen_protected | 0 | 1.12 | +0.11 |
| C_unfrozen_protected (anchor 1) | 0 | 1.18 | +0.16 |
| C_unfrozen_anchor3 | 0 | 1.12 | +0.07 |
| C_unfrozen_anchor5 | 1 (book14-tail1) | 5.47 | +5.94 |

In the anchor-5 run the recurrence diverges on ONE window (the second held-out tail window of book 14):
the hidden state is 5.5 times larger than native and 118 of 191 scored tokens get much worse. This is
not forgetting. The same window wobbled during reading in other runs too (largest spike: B +0.15,
anchor 3 +0.21, anchor 5 +6.05 after 10 books, then back to -0.05, then +2.94 at the end; A and
anchor 1 unfrozen: none). With one window this does not show that a stronger anchor causes it.
The anchor-5 "read books" numbers in the tables above include this window: without book 14 the read
books go 0.129 -> 0.149 (right after -> end).
