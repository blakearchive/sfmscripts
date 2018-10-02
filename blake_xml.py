#!/usr/bin/env python
import os
import re
import glob
from lxml import etree


class BlakeXML:
    """XML representation of a copy in the Blake Archive.

    Corresponds with one Blake xml file. Contains descriptions of each
    object (plate/page/etc) in the copy.
    """
    def __init__(self, path):
        self.path = path
        self.xml = self.parse_xml()

    def parse_xml(self):
        """Return etree read from xml file."""
        with open(self.path, 'r', encoding='utf-8') as xmlfile:
            return etree.parse(xmlfile)

    def objects(self):
        """Return generator that yields each object(plate/page) in the xml."""
        return [XMLObject(x, self) for x in self.xml.xpath('//objdesc/desc')]


class XMLObject:
    """XML representation of an object (plate/page/etc) in a copy."""

    def __init__(self, xml, blake_xml):
        self.xml = xml
        self.parent = blake_xml
        self.desc_id = self.xml.attrib['id']

    def text(self):
        """Return transcription text, with some transformations."""
        transcription = ''
        for line in self.xml.xpath('phystext//l'):
            # text is mainly in <l> nodes, but those <l> nodes can also
            # have child nodes that include text. Some of that text is desired
            # (e.g. from child <phystext> nodes).
            # <note> child nodes may have text that should not be included.
            # Delete note nodes then provide all (i.e. including nested)
            # text in <l>
            for note in line.findall('.//note'):
                note.getparent().remove(note)

            # some nodes contain <space/> nodes in place of whitespace, e.g.:
            #       Jehovah<space extent="1"/>What Vengeance dost thou require
            # Replace these with a single space. They may represent multiple
            #   spaces, but we end up trimming contiguous whitespace anyway.
            for space in line.findall('space'):
                space.text = ' '

            text = ''.join(line.itertext())

            if text == '':
                continue
            # Some xml files have line text nodes split across two or more
            # lines of the xml file. Those line breaks aren't part of
            # the transcription. Replace newlines or a contiguous
            # set of newlines with a single space.
            # Also, replace contiguous spaces with a single space, per
            # what has previously been done for superfastmatch.
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            transcription += text + '\n'
        return transcription.rstrip()

    def write_text(self, path=None):
        """Write transformed transcription text to file."""
        filename = self.desc_id + '.txt'
        fullpath = os.path.join(path, filename)
        with open(fullpath, 'w', encoding='utf-8') as ofile:
            ofile.write(self.text())

if __name__ == '__main__':
    # Extract transcriptions from files in xml_path and write to files
    # in txt_path

    xml_path = 'works/xml/'
    txt_path = 'works/text/'

    for filename in glob.glob(os.path.join(xml_path, '*.xml')):
        print('Extracting transcriptions from: ' + filename)
        blakefile = BlakeXML(filename)
        for obj in blakefile.objects():
            obj.write_text(txt_path)
