# -*- coding: utf-8 -*-
"""
Holds the code for cleaning out unwanted tags from the lxml
dom xpath.
"""
from .text import innerTrim
from .utils import ReplaceSequence


class DocumentCleaner(object):

    def __init__(self, config):
        """Set appropriate tag names and regexes of tags to remove
        from the HTML
        """
        self.config = config
        self.parser = self.config.get_parser()
        self.remove_nodes_re = (
            "^side$|combx|retweet|mediaarticlerelated|menucontainer|"
            "navbar|storytopbar-bucket|utility-bar|inline-share-tools"
            "|comment|PopularQuestions|contact|foot|footer|Footer|footnote"
            "|cnn_strycaptiontxt|cnn_html_slideshow|cnn_strylftcntnt"
            "|links|meta$|shoutbox|sponsor"
            "|tags|socialnetworking|socialNetworking|cnnStryHghLght"
            "|cnn_stryspcvbx|^inset$|pagetools|post-attributes"
            "|welcome_form|contentTools2|the_answers"
            "|communitypromo|runaroundLeft|subscribe|vcard|articleheadings"
            "|^date$|^print$|popup|author-dropdown|tools|socialtools|byline"
            "|konafilter|KonaFilter|breadcrumbs|^fn$|wp-caption-text"
            "|legende|ajoutVideo|timestamp|js_replies"
        )
        self.regexp_namespace = "http://exslt.org/regular-expressions"
        self.naughty_ids_re = (
            "//*[re:test(@id, '%s', 'i')]" % self.remove_nodes_re)
        self.naughty_classes_re = (
            "//*[re:test(@class, '%s', 'i')]" % self.remove_nodes_re)
        self.naughty_names_re = (
            "//*[re:test(@name, '%s', 'i')]" % self.remove_nodes_re)
        self.div_to_p_re = r"<(a|blockquote|dl|div|img|ol|p|pre|table|ul)"
        self.caption_re = "^caption$"
        self.google_re = " google "
        self.entries_re = "^[^entry-]more.*$"
        self.facebook_re = "[^-]facebook"
        self.facebook_braodcasting_re = "facebook-broadcasting"
        self.twitter_re = "[^-]twitter"
        self.tablines_replacements = ReplaceSequence()\
            .create("\n", "\n\n")\
            .append("\t")\
            .append("^\\s+$")

    def clean(self, doc_to_clean):
        """Remove chunks of the DOM as specified
        """
        doc_to_clean = self.clean_body_classes(doc_to_clean)
        doc_to_clean = self.clean_article_tags(doc_to_clean)
        doc_to_clean = self.clean_em_tags(doc_to_clean)
        doc_to_clean = self.remove_drop_caps(doc_to_clean)
        doc_to_clean = self.remove_scripts_styles(doc_to_clean)
        doc_to_clean = self.clean_bad_tags(doc_to_clean)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.caption_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.google_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.entries_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.facebook_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean,
                                               self.facebook_braodcasting_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.twitter_re)
        doc_to_clean = self.clean_para_spans(doc_to_clean)
        doc_to_clean = self.div_to_para(doc_to_clean, 'div')
        doc_to_clean = self.span_to_para(doc_to_clean)
        return doc_to_clean

    def clean_body_classes(self, doc):
        """Removes the `class` attribute from the <body> tag because
        if there is a bad match, the entire DOM will be empty!
        """
        elements = self.parser.getElementsByTag(doc, tag="body")
        if elements:
            self.parser.delAttribute(elements[0], attr="class")
        return doc

    def clean_article_tags(self, doc):
        articles = self.parser.getElementsByTag(doc, tag='article')
        for article in articles:
            for attr in ['id', 'name', 'class']:
                self.parser.delAttribute(article, attr=attr)
        return doc

    def clean_em_tags(self, doc):
        ems = self.parser.getElementsByTag(doc, tag='em')
        for node in ems:
            images = self.parser.getElementsByTag(node, tag='img')
            if len(images) == 0:
                self.parser.drop_tag(node)
        return doc

    def remove_drop_caps(self, doc):
        items = self.parser.css_select(doc, 'span[class~=dropcap], '
                                       'span[class~=drop_cap]')
        for item in items:
            self.parser.drop_tag(item)
        return doc

    def remove_scripts_styles(self, doc):
        # remove scripts
        scripts = self.parser.getElementsByTag(doc, tag='script')
        for item in scripts:
            self.parser.remove(item)
        # remove styles
        styles = self.parser.getElementsByTag(doc, tag='style')
        for item in styles:
            self.parser.remove(item)
        # remove comments
        comments = self.parser.getComments(doc)
        for item in comments:
            self.parser.remove(item)

        return doc

    def clean_bad_tags(self, doc):
        # ids
        naughty_list = self.parser.xpath_re(doc, self.naughty_ids_re)
        for node in naughty_list:
            self.parser.remove(node)
        # class
        naughty_classes = self.parser.xpath_re(doc, self.naughty_classes_re)
        for node in naughty_classes:
            self.parser.remove(node)
        # name
        naughty_names = self.parser.xpath_re(doc, self.naughty_names_re)
        for node in naughty_names:
            self.parser.remove(node)
        return doc

    def remove_nodes_regex(self, doc, pattern):
        for selector in ['id', 'class']:
            reg = "//*[re:test(@%s, '%s', 'i')]" % (selector, pattern)
            naughty_list = self.parser.xpath_re(doc, reg)
            for node in naughty_list:
                self.parser.remove(node)
        return doc

    def clean_para_spans(self, doc):
        spans = self.parser.css_select(doc, 'p span')
        for item in spans:
            self.parser.drop_tag(item)
        return doc

    def get_replacement_nodes(self, div):
        """
            Puts the content of div element (text nodes and its inline siblings) inside <p></p>
        """
        # list of html inline elements, except <br>
        inline_elements = [
            'a', 'abbr', 'acronym', 'b', 'basefont', 'bdo', 'big',
            'cite', 'code', 'dfn', 'em', 'font', 'i', 'input', 'kbd',
            'label', 'q', 's', 'samp', 'select', 'small', 'span', 'strike',
            'strong', 'sub', 'sup', 'textarea', 'tt', 'u', 'var'
        ]
        # list of candidates (inline elements and text nodes) to wrap with <p></p> element
        nodes_to_wrap = []
        # set this flag, when nodes_to_wrap contains at least one text node
        text_node_inside = False

        # childNodesWithText will wrap all text nodes with <text></text> element
        kids = self.parser.childNodesWithText(div)

        for kid in kids:
            inline_or_text = self.parser.getTag(
                kid) in inline_elements or self.parser.isTextNode(kid)
            is_last_child = kids[-1] == kid
            if inline_or_text:
                if self.parser.isTextNode(kid):
                    text_node_inside = True
                nodes_to_wrap.append(kid)

            if not inline_or_text or is_last_child:
                if (len(nodes_to_wrap) == 1 and text_node_inside and
                        innerTrim(nodes_to_wrap[0].text) == ''):
                    # saving white-space without creating empty <p>
                    self.parser.addprevious(nodes_to_wrap[0], kid)
                    # drop tag, but save text content
                    self.parser.drop_tag(nodes_to_wrap[0])
                elif len(nodes_to_wrap) and text_node_inside:
                    # create and insert new <p></p> element in right place
                    new_paragraph = self.parser.createElement(tag='p')
                    self.parser.addprevious(new_paragraph, kid)

                    # new paragraph will produce line break, should replace <br> tag (at least
                    # first occurrence)
                    if self.parser.getTag(kid) == 'br':
                        self.parser.drop_tag(kid)

                    # append text nodes and inline elements into the paragraph element
                    for n in nodes_to_wrap:
                        if self.parser.isTextNode(n):
                            if len(new_paragraph):
                                new_paragraph[-1].tail = n.text
                            else:
                                new_paragraph.text = n.text
                            # remove <text> nodes and their content
                            self.parser.drop_tree(n)
                        else:
                            # lxml append method moves element from one place to another
                            # and we dont need to remove it manually from an old place
                            self.parser.appendChild(new_paragraph, n)

                nodes_to_wrap = []
                text_node_inside = False

        return list(div)

    def replace_with_para(self, doc, div):
        self.parser.replaceTag(div, 'p')

    def div_to_para(self, doc, dom_type):
        bad_divs = 0
        else_divs = 0
        divs = self.parser.getElementsByTag(doc, tag=dom_type)
        tags = ['a', 'blockquote', 'dl', 'div', 'img', 'ol', 'p',
                'pre', 'table', 'ul']
        for div in divs:
            # items = self.parser.getElementsByTags(div, tags)
            # if div is not None and len(items) == 0:
            #     self.replace_with_para(doc, div)
            #     bad_divs += 1
            # el
            if div is not None:
                replace_nodes = self.get_replacement_nodes(div)
                replace_nodes = [n for n in replace_nodes if n is not None]
                div.clear()
                for i, node in enumerate(replace_nodes):
                    div.insert(i, node)
                else_divs += 1
        return doc

    def span_to_para(self, doc):
        spans_to_ignore = self.parser.css_select(doc, 'p span')
        spans_to_convert = doc.xpath('.//*[self::div|self::article]/span')

        for span in spans_to_convert:
            if span not in spans_to_ignore:
                self.replace_with_para(doc, span)
        return doc
