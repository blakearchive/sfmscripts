#!/usr/bin/env python
import csv
import time
import simplejson as json
import requests
import yaml

#
# Specify Superfastmatch API connection info in superfast.yaml
#


class SuperfastAPI:
    """Simple wrapper for Superfastmatch API."""
    def __init__(self, addr, port):
        self.addr = addr
        self.port = str(port)
        self.base_url = "http://" + self.addr + ":" + self.port + "/"

    @classmethod
    def from_cfg(cls, filename):
        """Initializes SuperfastAPI from a YAML config file.

        YAML file contains:
            addr: www.example.com  (or by IP, e.g.: 127.0.0.1)
            port: 8080
        """
        with open(filename) as infile:
            cfg = yaml.safe_load(infile)
        addr = cfg['addr']
        port = cfg['port']
        return BlakeSuperfast(addr, port)

    def get(self, lst, yield_json=True):
        """Makes an api call to url formed from list of url elements.

        Sets url as url
        Raises an error if it receives an unsuccessful response.

        For example,
            $ get(['document', '1', '89'])
                => calls base_url:port/document/1/89
            $ get(['document/1/89'])
                => calls base_url:port/document/1/89

        Arguments:
        lst: A list of elements that form the endpoint url.
            e.g. $ get(['document', '1', '89'])
                    => calls base_url:port/document/1/89
                 $ get(['document/1/89'])
                    => also calls base_url:port/document/1/89
        yield_json: Returns deserialized json response when True, response text
                    when False (default True)
        """
        try:
            url = self.base_url + '/'.join(lst)
        except TypeError:
            url = self.base_url + '/'.join(str(x) for x in lst)
        self.url = url
        r = requests.get(url)
        r.raise_for_status()
        self.response = r
        if yield_json:
            return json.loads(r.text)
        else:
            return r.text

    def doc_factory(self, doctype, docid, api=None):
        api = api or self
        return SuperfastDoc(doctype, docid, api=api)

    def documents(self, perpage=100):
        """Returns generator that yields all documents in the api."""
        perpage = str(perpage)
        more_pages = True
        next_cursor = False
        while more_pages:
            if next_cursor:
                paginate = '?limit=' + perpage + '&cursor=' + next_cursor
            else:
                paginate = '?limit=' + perpage
            page = self.get(['document', paginate])
            next_cursor = page['cursors']['next']
            more_pages = next_cursor != ''
            for row in page['rows']:
                yield self.doc_factory(row['doctype'], row['docid'],
                                       api=self)


class BlakeSuperfast(SuperfastAPI):
    """Extends SuperfastAPI with Blake Archive-specific functions."""

    def doc_factory(self, doctype, docid, api=None):
        """Initializes and returns a BlakeDoc object.

        Overrides SuperfastAPI.doc_factory which returns SuperfastDoc objects.
        """
        api = api or self
        return BlakeDoc(doctype, docid, api=api)

    def export_fragments(self, filename, iterator=None, matrix_csv_path=None):
        """Write matches/fragments to csv.

        filename: outfile path/name
        iterator: iterable objects containing BlakeDocs; default iterates
                  through all documents in the API
        matrix_csv_path: a blake-relations.csv file (which includes a column
                  specifying matches to exclude because the objects are from
                  the same matrix). None/default value means no exclusions.
        """
        iterator = iterator or self.documents()
        if matrix_csv_path:
            SuperfastDocmatch.exclusions = MatrixRelations(
                                                    matrix_csv_path).matrices
        with open(filename, 'w', encoding='utf-8', newline='') as ofile:
            csvwriter = csv.writer(ofile)
            csvwriter.writerow(
                ['primary_desc_id', 'match_desc_id', 'fragment']
            )
            for primary_doc in iterator:
                print('original: ' + primary_doc.title + ' (doctype: ' +
                      str(primary_doc.doctype) + ' docid: ' +
                      str(primary_doc.docid) + ')')
                time.sleep(0.1)
                for match in primary_doc.matches():
                    time.sleep(0.1)
                    if matrix_csv_path and match.excluded():
                            continue
                    print('    matching: ' + match.matching_doc.title)
                    for fragment in match.fragments():
                        csvwriter.writerow([primary_doc.desc_id,
                                            fragment.doc.desc_id,
                                            fragment.text_cleaned()])

try:
    API = BlakeSuperfast.from_cfg('superfast.yaml')
except FileNotFoundError:
    # connection info is expected to be in superfast.yaml but it's not
    # a requirement (i.e. if you later set it manually.
    API = BlakeSuperfast('example.com', 8080)


class SuperfastDoc:
    """Represents a Superfastmatch document.

    Created using doctype/docid, e.g:
        doc = SuperfastDoc(1, 89)

    Or from json file or dict, e.g.:
        doc = SuperfastDoc.from_json('foo.json')

    Note that if documents are removed and reloaded into Superfastmatch,
    SuperfastDoc(1, 89) post-reload may represent a different document than
    it did pre-reload.
    """
    def __init__(self, doctype=None, docid=None, api=API, dct=None):
        self.api = api
        if dct:
            self.__dict__ = dct
        else:
            self.get_json(doctype, docid)
        self.json_keys = list(self.__dict__.keys()).copy()

    @classmethod
    def from_json(cls, file_or_dict):
        """Returns SuperfastDoc created via json file or dict, not API."""
        try:
            with open(file_or_dict, 'r') as json_file:
                    doc_json = json.load(json_file)
        except TypeError:
            doc_json = file_or_dict
        return cls(dct=doc_json)

    def get_json(self, doctype, docid):
        """Retrieves document json via api."""
        self.__dict__ = self.api.get(['document', doctype, docid])

    def fragment(self, begin, length):
        """Returns text substring from doc."""
        return self.text[begin:begin+length]

    def matches(self):
        """Generator that yields matches as SuperfastDocmatch objects."""
        return (SuperfastDocmatch(self, row_dct=row)
                for row in self.documents['rows'])

    def orig_json(self):
        """Returns original json/dict."""
        return {key: self.__dict__[key] for key in self.json_keys}

    def write_json(self, filename, encoding='utf-8'):
        """Writes original json/dict to file."""
        with open(filename, 'w', encoding=encoding) as ofile:
            ofile.write(json.dumps(self.orig_json(), encoding=encoding))


class BlakeDoc(SuperfastDoc):
    """Blake Archive-specific document functions

    Primarily adds name/title parsing.
    """

    def __init__(self, doctype=None, docid=None, api=API, dct=None):
        super().__init__(doctype, docid, api, dct)
        self.parse_title()

    def __repr__(self):
        return '<BlakeDoc ' + self.desc_id + '>'

    def parse_title(self):
        """Sets attributes for title and components that form the title.

        For example:
        title:   vda.h.illbk.07.txt
        desc_id: vda.h.illbk.07
        work:    vda
        copy:    h
        form:    illbk
        page:    07

        For non-conforming titles, work/copy/form/page are None
        """
        # All documents are said to end in ".txt", but so long as they all have
        # /some/ final extension-like segment, this derivation of desc_id
        # will work.
        self.desc_id = '.'.join(self.title.split('.')[:-1])

        # If superfast titles have five segments, we can derive subcomponents.
        # If there are fewer than five segments, we're not sure which
        #    segment(s) are missing, and do not derive subcomponents.
        try:
            self.work, self.copy, self.form, self.page, _ = (
                self.title.split('.')
            )
        except ValueError:
            self.work = None
            self.copy = None
            self.form = None
            self.page = None


class SuperfastDocmatch:
    """Relates two SuperfastDocs that share one or more fragments.

    One SuperfastDocmatch object contains any/all matching fragments.
    When initializing, pass the matching doc as either row_dct or match_doc
        match_doc needs to be an actual SuperfastDoc object.
        row_dct needs to be a row of ['documents']['rows'] from the json,
            i.e. a dict like:
                {'fragments': [[28, 30, 370, 4200547186],
                               [399, 401, 295, 2671570340],
                               ...]
                'characters': 1498, 'docid': 199, 'doctype': 1,
                'group': 'fixtures/blake/Transcriptions',
                'title': 'vda.g.illbk.07.txt',
                'fragment_count': 4}
    """
    def __init__(self, primary_doc, row_dct=None, match_doc=None, api=API):
        self.api = api
        self.primary_doc = primary_doc
        if match_doc:
            self.matching_doc = match_doc
        elif row_dct:
            self.data = row_dct
            self.matching_doc = BlakeDoc(
                self.data['doctype'], self.data['docid'], api=self.api
            )
        else:
            raise ValueError("row_dct or match_doc must be supplied")

    def excluded(self):
        """Checks whether matching_doc and primary_doc are from same matrix."""
        if not self.exclusions:
            raise ValueError("no matrix values are present")
        # same_matrix-ness is expected to be reciprocal, but reciprocality
        # depends on the csv. check both docs for whether other doc is from
        # the same matrix, and return True when either is.
        if (self.matching_doc.desc_id in
                self.exclusions.get(self.primary_doc.desc_id, [])
            or
            self.primary_doc.desc_id in
                self.exclusions.get(self.matching_doc.desc_id, [])):
            return True

    def fragments(self):
        "Generator that yields self's fragments as MatchFragment objects."
        return (MatchFragment(self.matching_doc, fragment_list)
                for fragment_list in self.data['fragments'])


class MatchFragment:
    """A particular portion of text from a particular document.

    Matching fragments may contain the same text as one another, but may
    have differing begin and end positions in their documents.

    doc:            a SuperfastDoc/BlakeDoc object
    fragment_list:  a list from the document json specifying begin/end points
                        e.g. [28, 30, 370, 4200547186]
                    where the elements are:
                        start position of match text in primary doc (28),
                        start position of match text in matching doc (30),
                        length of the fragment (370),
                        hash of the fragment (4200547186),
    """
    def __init__(self, doc, fragment_list):
        self.doc = doc
        self.lst = fragment_list
        self.begin = int(self.lst[1])
        self.length = int(self.lst[2])
        self.text = self.doc.fragment(self.begin, self.length)

    def text_cleaned(self):
        """Returns fragment text with any modifications the output requires."""
        return self.text.replace('\n', '<br>')


class MatrixRelations:
    """Loads and queries matrix relation info from csv."""

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.load_relations()

    def load_relations(self):
        """Load matrix relations from csv into dict and sets as self.matrices.

        matrices looks like:
            {desc.id.1: [same.matrix.1, same.matrix.2],
             desc.id.2: ...}

        We presume matrices[same.matrix.1] will include desc.id.1, and it will
        so long as the csv record for same.matrix.1 reciprocally lists
        desc.id.1, but there's no guarantee.

        Objs with no matrix relations are not stored in the dict.
        """
        with open(self.csv_path, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile)
            matrices = {}
            for row in csvreader:
                if row['same_matrix_ids'] == '':
                    continue
                same_matrix_ids = row['same_matrix_ids'].split(',')
                try:
                    matrices[row['desc_id']] += same_matrix_ids
                except KeyError:
                    matrices[row['desc_id']] = same_matrix_ids
            self.matrices = matrices

    def same_matrix(self, doc, otherdoc):
        """True when objects are from the same matrix"""
        try:
            if doc.desc_id in self.matrices.get(otherdoc.desc_id):
                return True
        except TypeError:
            pass
        return False


if __name__ == '__main__':
    # Exports a csv of matches/fragments, excluding matches
    # from the same matrix (per the matrix_relations_file)
    outfile = 'blake_superfast_matches.csv'
    matrix_relations_file = 'blake-relations.csv'
    print('Exporting matches/fragments to: ' + outfile)
    try:
        API.export_fragments(
            outfile, matrix_csv_path=matrix_relations_file
        )
    except FileNotFoundError:
        print('Exclude/matrix_relations file not found. Not excluding matches '
              'from the same matrix')
