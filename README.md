# Blake Superfastmatch

Provides a (very minimal) Superfastmatch API wrapper and utilities to export matches/fragments to from Superfastmatch to csv. Also provides utilities to extract transcriptions from Blake Archive object xml (suitable for input for Superfastmatch).

## Setup

- tested in python 3.4.3, 3.6.0
- ```pip install requests simplejson PyYAML pytest```
- install lxml
- specify Superfastmatch address in superfast.yaml

  As in:

  ```yaml
  addr: www.example.com  # or by IP, e.g.: 127.0.0.1
  port: 8080
  ```

- Run tests: ```pytest```

## Usage

- Extract transcriptions from xml: ```python blake_xml.py```
- Export matches/fragments from Superfastmatch:
    ```python blake_superfast.py```

## Superfastmatch implementation

### API

```python
import blake_superfast as blake

api = blake.API
api.get(['status'])          # calls http://example.com:8080/status
api.get(['document', 1, 89]) # calls http://example.com:8080/document/1/89

# do something to all the documents
for doc in api.documents():
    do_something(doc)

# get the first 50 documents
import itertools
docs = itertools.islice(api.documents(), 0, 50)
```

### Documents, matches, and fragments

```python

# retrieve a doc by doctype and docid
# note that documents may not have static doctype/docids
# if they are removed and re-added to superfastmatch
doc = blake.BlakeDoc(1, 89)

# get a doc from json or json file
doc = blake.BlakeDoc(from_json='data/vda.h.illbk.07.json')

doc.desc_id          #=> 'vda.h.illbk.07'

# get a match which relates doc to a matching_doc
match = next(doc.matches())

match.primary_doc    #=> 'vda.h.illbk.07'
match.matching_doc   #=> 'vda.g.illbk.07'

# each match will contain any/all matching fragments
# between the docs
fragments = list(match.fragments())

fragments[0].text    #=> 'and in what houses dwell...'
```

### Excluding matches between objects from the Same Matrix

```python
same_matrix_dict = blake.MatrixRelations('blake-relations.csv').matrices
    #=> {
    #       'vda.mpi.illbk.03':
    #           ['bb136.a.spb.20', 'vda.a-proof.illbk.03',
    #            'vda.a.illbk.02',...],
    #       ...
    #       'thel.a-proof.05.illbk': ['thel.h.illbk.07']
    #   }
blake.SuperfastDocmatch.exclusions = same_matrix_dict

# 'vda.h.illbk.07' and 'vda.g.illbk.07' are from the same matrix
match.excluded()     #=> True
```

### Exporting fragments from Superfastmatch to a csv

```console
# python blake_superfast.py [outpath] [exclusions_csv_path]
python blake_superfast.py my_export.csv blake-relations.csv
```

or

```python
blake.api.export_fragments(
  'my_export.csv', matrix_csv_path='blake-relations.csv'
)
```

Writes a csv like:

```text
doc001,matchdoc001,fragment001
doc001,matchdoc001,fragment002
...
matchdoc001,doc001,fragment001
matchdoc001,doc001,fragment002
```

## XML extraction implementation

### BlakeXML and XMLObject

XMLObject is Object as in XML plate/page.

```python
import blake_xml

xml_file = blake_xml.BlakeXML('data/vda.h.xml')

# get XML as etree
xml_file.xml    #=> <lxml.etree._ElementTree object at 0x00DFFC10>

# get a list of specific objects (i.e. plate/page) from xml
my_objects = xml_file.objects()

obj = my_objects[1]
obj.desc_id     #=> 'vda.h.illbk.02'
obj.parent      # returns xml_file
```

### Transcriptions

Note: Expect text to be cleaned up some. See function for details. (For example, contiguous whitespace may be trimmed to a single space, text may be stripped, "note" nodes/text removed, "space" nodes interpreted as a space.)

```python
# get transcription
obj.text()      #=> 'VISIONS\nof\nthe Daughters of\nAlbion\n...'

# write transcription...
# ...to .txt file named after the desc_id
obj.write_text
# ...to arbitrary path
obj.write_text(path='other_file.txt')
```

Objects with no text will have empty files written.
