"""Synthetic, PII-free parser fixtures; no completed owner Word in the repo."""

import copy
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import import_completed_review as review


def fixture():
    source = {'sample': {}}
    template, completed = [], []
    for ti, (group, size) in enumerate(zip(
            ['fiados', 'fiados', 'rejections', 'weeks', 'assumptions'], [6, 6, 4, 4, 3], strict=True), 1):
        headers = ['id', 'data', 'response'] if ti != 5 else ['id', 'response', 'correction']
        if group == 'weeks':
            headers = ['id', 'requests', 'grants', 'response']
        blank, filled = [headers], [headers]
        refs = source['sample'].setdefault(group, [])
        for i in range(size):
            n = len(refs)
            if group == 'fiados':
                ref = {'id': f'SET5-D1-L{n:05}', 'response': 'Habitual' if n < 3 else 'Posible'}
            elif group == 'rejections':
                ref = {'id': f'SET5-D1-A{n:05}', 'response': 'Habitual'}
            elif group == 'weeks':
                ref = {'world': 'SET5-D1', 'week_start': f'2026-01-{i+1:02}',
                       'grants': 12, 'grant_clients': 9, 'response': 'Habitual' if i < 2 else 'Posible'}
            else:
                ref = {'id': f'assumption_{i}', 'response': 'no' if i == 0 else 'posible'}
            refs.append(ref)
            key = ref.get('id', ref.get('world', '') + '\n' + ref.get('week_start', ''))
            row = [key, '12 / 9' if group == 'weeks' else 'data', '']
            if ti == 5:
                row = [key, '', '']
            if group == 'weeks':
                row = [key, '12 / 9', '12 / 9', '']
            blank.append(row)
            answer = row.copy()
            answer[1 if ti == 5 else len(headers) - 1] = ref['response']
            if ti == 5:
                answer[2] = 'Synthetic correction'
            filled.append(answer)
        template.append(blank)
        completed.append(filled)
    source['sample'].update(fiados_reviewed=12, rejections_reviewed=4,
                            weeks_reviewed=4, assumptions_reviewed=3)
    return completed, template, source


class ImportTests(unittest.TestCase):
    def test_valid_and_raw_case_preserved(self):
        records = review.validate_tables(*fixture())
        self.assertEqual(len(records), 23)
        self.assertEqual(records[-1]['raw_response'], 'posible')
        self.assertEqual(records[2]['classification_canonical'], 'habitual')

    def test_invalid_blank_and_case_coercion(self):
        for value in ['', ' ', 'approved', 'habitual']:
            with self.subTest(value=value):
                tables, template, source = fixture()
                tables[0][1][2] = value
                with self.assertRaises(ValueError):
                    review.validate_tables(tables, template, source)

    def test_source_counts_exact_text_and_ids(self):
        for mutation in ['missing', 'declared_count', 'response', 'id', 'nonresponse', 'correction', 'table']:
            with self.subTest(mutation=mutation):
                tables, template, source = fixture()
                if mutation == 'missing':
                    source['sample']['fiados'].pop()
                elif mutation == 'declared_count':
                    source['sample']['fiados_reviewed'] = 540
                elif mutation == 'response':
                    source['sample']['fiados'][0]['response'] = 'Posible'
                elif mutation == 'id':
                    source['sample']['fiados'][0]['id'] = 'SET5-D1-L99999'
                elif mutation == 'nonresponse':
                    tables[0][1][1] = 'altered amount'
                elif mutation == 'correction':
                    tables[4][1][2] = ''
                else:
                    tables.pop()
                with self.assertRaises(ValueError):
                    review.validate_tables(tables, template, source)

    def test_xml_linebreaks_and_hidden_review_markup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.docx'
            with ZipFile(path, 'w') as archive:
                archive.writestr('word/document.xml',
                    f'<w:document xmlns:w="{review.NS["w"]}"><w:body>'
                    '<w:p><w:r><w:t>Prompt:</w:t><w:br/><w:t>answer</w:t></w:r></w:p>'
                    '<w:ins/><w:del/><w:commentReference/>'
                    '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>posible</w:t></w:r></w:p>'
                    '</w:tc></w:tr></w:tbl></w:body></w:document>')
                archive.writestr('word/comments.xml', f'<w:comments xmlns:w="{review.NS["w"]}"><w:comment/></w:comments>')
            paragraphs, tables, counts = review.parse_docx(path)
            self.assertEqual(paragraphs, ['Prompt:\nanswer'])
            self.assertEqual(tables, [[['posible']]])
            self.assertEqual([counts[k] for k in ['comments', 'ins', 'del', 'commentReference']], [1, 1, 1, 1])

    def test_markdown_multiline_blank_template(self):
        result = review.markdown_tables('| Caso inventado | response |\n| --- | --- |\n| A<br>B |  |\n')
        self.assertEqual(result[0][1], ['A\nB', ''])

    def test_template_not_mutated(self):
        tables, template, source = fixture()
        before = copy.deepcopy(template)
        review.validate_tables(tables, template, source)
        self.assertEqual(template, before)


if __name__ == '__main__':
    unittest.main()
