import concurrent.futures

import deepl
from tqdm import tqdm

KEY = "xxxxxxxxxxxxx"
LANG = 'ZH'


class TranslatorSRT:
    def __init__(self, key, target_lang, print_result=False):
        self.deepl_translator = deepl.Translator(key)
        self.target_lang = target_lang
        self.print_result = print_result
        self.is_translating = False
        self.line_count = 0
        self.progress_bar = None

    @staticmethod
    def _line_needs_translate(line):
        # Is blank line
        if not line.strip():
            return False
        # Pure number (subtitle index)
        elif line.replace(' ', '').isdigit():
            return False
        # Including '-->' (timestamp)
        elif '-->' in line:
            return False
        else:
            return True

    @staticmethod
    def _html_tag_splitter(text):
        # HTML tags list for text style used in srt subtitle
        # TODO: Maybe more tags
        tags = ['i', 'b', 'u', 'em', 'strong']
        for tag in tags:
            if f"<{tag}>" in text:
                stripped_text = text.replace(f"<{tag}>", '').replace(f"</{tag}>", '')
                return stripped_text, f"<{tag}>", f"</{tag}>"
        raise ValueError("No HTML tags found.")

    @staticmethod
    def _read_file_to_indexed_lines(in_file):
        try:
            with open(in_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                lines = [line.rstrip() for line in lines]
                original_lines_with_index = list(zip(range(len(lines)), lines))
                return original_lines_with_index
        except FileNotFoundError:
            print(f"Error: The file {in_file} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")

    @staticmethod
    def _write_srt(translated_lines, out_file):
        try:
            with open(out_file, 'w', encoding='utf-8') as file:
                file.writelines([line + '\n' for line in translated_lines])
        except FileNotFoundError:
            print(f"Error: The file {out_file} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def _translator(self, text):
        result = self.deepl_translator.translate_text(text, target_lang=self.target_lang)
        return result.text

    def _translate_line(self, text):
        result = text
        if self._line_needs_translate(text):
            # Line with HTML tag
            if '</' in text:
                real_content, start_tag, end_tag = self._html_tag_splitter(text)
                content_result = self._translator(real_content)
                result = f"{start_tag}{content_result}{end_tag}"
            else:
                result = self._translator(text)
            if self.print_result:
                print(f'{text} => {result}')
        return result

    def _translate_indexed_tuple(self, index_content_tuple):
        index, content = index_content_tuple
        new_content = self._translate_line(content)
        self.progress_bar.update(1)
        return index, new_content

    def _translate_indexed_lines(self, original_lines_with_index):
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
            results_indexed_tuple = list(executor.map(self._translate_indexed_tuple, original_lines_with_index))
            sorted_result = sorted(results_indexed_tuple, key=lambda x: x[0])
            sorted_list = [item[1] for item in sorted_result]
            return sorted_list

    def translate_file(self, in_file, out_file):
        self.is_translating = True
        indexed_lines = self._read_file_to_indexed_lines(in_file)
        self.line_count = len(indexed_lines)
        self.progress_bar = tqdm(total=self.line_count, desc="Translating", unit="line")
        translated_lines = self._translate_indexed_lines(indexed_lines)
        self._write_srt(translated_lines, out_file)

        self.line_count = 0
        self.is_translating = False
        self.progress_bar.close()


def main():
    in_file_path = "test.srt"
    out_file_path = "test_chs.srt"
    translator = TranslatorSRT(KEY, LANG)
    translator.translate_file(in_file_path, out_file_path)


if __name__ == "__main__":
    main()
