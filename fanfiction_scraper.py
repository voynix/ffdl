#! /usr/bin/python

import argparse
import os
import re

url = "hella"
tempfile = "temp"
preprocfile = "temp2"
outfile = "out"
chapter = 1
num_chapters = 1
title = "hella"
chapter_path = "hella"
chapter_titles = []
default_chapter_titles = True
chapter_text = "hella"
author = "hella"

style = "null"
add_style = False

outfolder = "null"
custom_outfolder = False

parser = argparse.ArgumentParser(description = "A script to download stories from fanfiction.net")
parser.add_argument('url', metavar = 'URL', help = 'The URL of the story to download (for multichapter stories this may be the URL of any chapter of the story)')
parser.add_argument('-s', '--style', metavar = 'STYLE_FILE', help = 'A file containing CSS rules to be applied to the story')
parser.add_argument('-o', '--output-folder', metavar = 'OUTPUT_FOLDER', help = 'The folder to download the story to')

# process command-line args
args = parser.parse_args()
url = args.url
if args.style is not None:
    style = args.style
    add_style = True
if args.output_folder is not None:
    outfolder = args.output_folder
    custom_outfolder = True

# only do these things once, since they're per story not per chapter
# found_canonical_url = False
found_title = False
found_author = False
found_chapter_titles = False

# workaround for ff.net inconsistency
# in most stories/chapters the text is on one line,
# but in some there are line breaks
in_broken_story_text = False

url_parts = url.split('/')
canonical_url = 'https://www.fanfiction.net/s/' + url_parts[-3] + '/{0!s}/' + url_parts[-1]

while chapter <= num_chapters:

    # download the file
    os.system("curl " + canonical_url.format(chapter) + " > " + tempfile)

    # do some preprocessing
    with open(tempfile, 'r') as input:
        with open(preprocfile, 'w') as output:
            for line in input:
                #fix case fuckery
                line = re.sub(r'<P', '<p', line)
                line = re.sub(r'</P', '</p', line)
                #LF supremacy; fuck to CR
                line = re.sub(r'\r', '\n', line)
                output.write(line)

    with open(preprocfile, 'r') as input:
        for line in input:
            #grab canonical URL
            #if not found_canonical_url and line.find("<META NAME='view") > -1:
            #    parts = line.split(' ')
            #    for part in parts:
            #        if part[:4] == 'href':
            #            canonical_url = 'http:/' + part[6:-2]
            #            canonical_url = '/{0!s}/'.join(canonical_url.split('/1/'))
            #            found_canonical_url = True
            # grab title for multichapter stories
            if not found_title and line[:6] == '<title':
                cull_start = line.find(' Chapter ' + str(chapter))
                if cull_start > -1: #multiple chapters
                    title = line[7:cull_start]
                    chapter_path = title + '/{0!s}.html'
                    found_title = True
            # grab title for single chapter stories
            elif not found_title and line.find("var title = '") > -1:
                title_start = line.find("var title = '") + 13
                title = line[title_start:-3]
                title = re.sub('\+', ' ', title)
                found_title = True
            # grab author
            elif not found_author and line.find("'/u/") > -1: #hopefully this is reliable
                part = line.split('href')[1]
                beginning_of_name = part.find("'>") + 2
                end_of_name = part.find("</a>")
                author = part[beginning_of_name:end_of_name]
                found_author = True
            # grab chapter titles
            elif not found_chapter_titles and line.find('title="Chapter Navigation') > -1:
                start_of_list = line.find('<option')
                end_of_list = line.rfind('</select')
                title_list = line[start_of_list: end_of_list]
                chapter_titles = title_list.split('<option  value=')[1:] #remove empty first entry
                num_chapters = len(chapter_titles)
                for ch in xrange(1, num_chapters + 1):
                    title_string = chapter_titles[ch - 1]
                    target_string = str(ch) + '. '
                    beginning_of_title = title_string.find(target_string) + len(target_string)
                    chapter_titles[ch - 1] = str(ch) + '-' + title_string[beginning_of_title:]
                    if title_string[beginning_of_title:] != 'Chapter '+ str(ch):
                        default_chapter_titles = False
                found_chapter_titles = True
                if default_chapter_titles: # if no chapter titles, force to chapter number
                    for ch in xrange(0, num_chapters):
                        chapter_titles[ch] = str(ch + 1)
            # grab chapter text
            elif line[:21] == "<div class='storytext":
                # #fix case fuckery - do this more generally later maybe if needed
                text_start = line.find('<p')
                chapter_text = line[text_start:]
                # if we've got broken chapter text; see note above
                if len(chapter_text) < 100:
                    in_broken_story_text = True
                    continue
                # separate out paragraphs for nice html
                chapter_text = '</p>\n<p'.join(chapter_text.split('</p><p'))
            # keep grabbing chapter text; see note on in_broken_story_text above
            elif in_broken_story_text:
                if line[-7:] == '</div>\n':
                    in_broken_story_text = False
                    # replace newlines from suturing the lines together with spaces
                    chapter_text = ' '.join(chapter_text.split('\n'))
                    # separate out paragraphs for nice html
                    chapter_text = '</p>\n<p'.join(chapter_text.split('</p><p'))
                    continue
                chapter_text += line

    # calculate the final filename for the chapter and make a folder for the story if necessary
    if num_chapters > 1:
        if default_chapter_titles:
            filename = chapter_path.format(str(chapter))
        else:
            chapter_titles[chapter - 1] = re.sub(':', '-', chapter_titles[chapter - 1]) #regex to fix':' in filenames
            filename = chapter_path.format(chapter_titles[chapter - 1])
        folder_to_check = title
        if custom_outfolder:
            filename = outfolder + '/' + filename
            folder_to_check = outfolder + '/' + folder_to_check
        if not os.path.exists(folder_to_check):
            os.makedirs(folder_to_check)
    else:
        filename = title + '.html'
        if custom_outfolder:
            filename = outfolder + '/' + filename

    # move the temp file to its final location
    os.rename(tempfile, filename)

    # make the final file, output the data
    with open(filename, 'w') as output:
        output.write('<html>\n<head>\n<title>')
        # write title
        if num_chapters > 1:
            if default_chapter_titles:
                output.write(title + ' || Chapter ' + str(chapter))
            else:
                output.write(title + ' || ' + chapter_titles[chapter - 1])
        else:
            output.write(title)
        output.write("</title>\n<meta charset='utf-8'>") # to make unicode chars work!
        # write style
        if add_style:
            output.write('<style>')
            output.write(style)
            output.write('</style>')
        # write header
        output.write('<a href="' + canonical_url.format(chapter) + '">Source</a>')
        output.write('<br>By ' + author)
        output.write('<br><div class="navigation">') # top nav
        if chapter > 1:
            output.write('<a href="' + chapter_titles[chapter - 2] + '.html">Prev</a>')
        if chapter < num_chapters:
            output.write('<a href="' + chapter_titles[chapter] + '.html">Next</a>')
        output.write('</div>\n</head>')
        output.write('<body>\n<div id="chapter_title"><h1>')
        if num_chapters > 1:
            if default_chapter_titles: #chapter title
                output.write('Chapter ' + str(chapter))
            else:
                output.write(chapter_titles[chapter - 1])
        else:
            output.write(title)
        # write story
        output.write('</h1></div>')
        output.write('<div id="story">')
        output.write(chapter_text)
        output.write('</div>')
        # write footer
        output.write('<br><div class="navigation">') # bottom nav
        if chapter > 1:
            output.write('<a href="' + chapter_titles[chapter - 2] + '.html">Prev</a>')
        if chapter < num_chapters:
            output.write('<a href="' + chapter_titles[chapter] + '.html">Next</a>')
        output.write('</div>\n</body>\n</html>')

    # increment to next chapter
    chapter += 1

# delete the preprocfile
os.remove(preprocfile)

# YATTA!
