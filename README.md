payfilt is a python commandline tool that reads .TAB files detailing payments from my bankaccount.
Preferred python modules: argparse, csv, numpy, matplotlib (when making graphs, not yet)

It offers the following options:

--merchant "Public Food|Albert Heijn"

only show results for merchants that match "Public Food" or "Albert Heijn".


--list

show payments in following format (so if no 'Naam: ...' is given, use the information in the field that contains 'Albert Heijn / Public Food in the example .TAB file').
For card payments ('BEA, Betaalpas'), use the time from the field after the merchant name. So for the last line in the example line, use "NR:MCH4GF6D, 20.10.26/14:17", so the date_time field becomes 20261020_14:17.

Output:
```
Date_time      Town      name                amount
20231201       Zaandam   hollandsnieuwe      11.00
20250901_20:51 Rotterdam Albert Heijn Online 82.45
```

--wlist

Same as --list, but also show weeknumber and weekday. The last line in the example file becomes:

Output:
```
Date_time              Town        name          amount
20261020(43.2)_14:17   Rotterdam   Public Food   13.00
```

--daylist

don't show any information, just list days where payments were made (that match filters like --merchant)

Output:
```
20231201
20250901
```

--weekdaycount
calculate daylist, and from that list count the number of days that were in each week (ISO week convention).
Output:
2023.48, 1
2023.49, 2
