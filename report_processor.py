import os
import json
import docx
import zipfile
import xml.etree.ElementTree as ET
from langchain_gigachat.chat_models import GigaChat
from langchain_core.prompts import ChatPromptTemplate

class ReportEvaluator:
    def __init__(self, llm):
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_template(
            """Вы — преподаватель, оценивающий отчеты по лабораторным работам. 
            Ваша задача — тщательно проверить отчет и снизить баллы за ошибки или недочеты.

            ВАЖНО:
            - Максимальный балл ставится ТОЛЬКО при полном отсутствии ошибок и замечаний.
            - При наличии любых проблем баллы ОБЯЗАТЕЛЬНО снижаются.
            - Итоговый балл должен быть точно подсчитан с учетом всех вычетов.
            - Оценивайте СТРОГО по указанным критериям, не смешивая их между собой.

            Система штрафов (для каждого критерия отдельно):
            - Незначительные ошибки: -0.5 балла
            - Существенные ошибки: -1 балл
            - Критические ошибки: -2 балла и более

            Критерии оценки:
            {criteria}

            Содержание и стили отчета:
            {content}

            Требования к отчету (из методички):
            {requirements}

            Сводка по работе (из методички):
            {summary}

            Инструкции по оценке:
            1. Оцените каждый критерий отдельно, строго придерживаясь его описания.
            2. Для критерия проверки отчета на правильность, структуру и соответствие требованиям:
               - Проверяйте ТОЛЬКО содержание, расчеты и соответствие требованиям методички.
               - НЕ учитывайте здесь аспекты оформления (такие ка нумерация, шрифты и т.д.).
            3. Для критерия, где необходимо проверить ответы на вопросы:
               - Оценивайте ТОЛЬКО полноту и правильность ответов на вопросы.
               - Если раздел с вопросами есть, а ответов нет, то по этому критерию ставится 0.
            4. Для критерия оформление:
               - Рассматривайте ТОЛЬКО аспекты форматирования, стиля и общего вида отчета.
            5. Для каждого критерия:
               - Укажите начальный балл (максимальный для данного критерия).
               - Перечислите конкретные найденные ошибки и недочеты.
               - Укажите величину штрафа за каждую ошибку.
               - Вычтите все штрафы из начального балла.
               - Запишите итоговый балл по критерию.
            6. Общий комментарий по работе
            7. ФИО автора отчета с титульного листа работы
               
            Формат ответа:
            ###\n
            Критерий: <название критерия>
            Комментарий к оценке: <комментарий на той же строке>
            Штраф: <штраф>
            Итоговый балл: <балл за критерий>
            ###\n
            Критерий:
            Комментарий к оценке:
            Штраф:
            Итоговый балл:
            ...

            ФИО:
            """
        )
    
    def _extract_author_from_content(self, content):
        try:
            prompt = ChatPromptTemplate.from_template(
                """Найдите ФИО автора отчета в тексте. 
                Верните только ФИО, без дополнительного текста.
                Если ФИО не найдено, верните "Не найдено".
                ФИО находится НЕ в разделе "Проверил" и аналогичные.
                Скорее всего находится в разделе "Выполнил".
                В качестве ответа предоставь только ФИО.


                Текст отчета:
                {content}
                """
            )
            print(prompt)
            
            formatted_prompt = prompt.format(content=content)
            response = self.llm.invoke([{"role": "user", "content": formatted_prompt}])
            return response.content.strip()
        except Exception as e:
            return f"Ошибка при извлечении ФИО: {str(e)}"


    def evaluate(self, doc_path, criteria, requirements, summary):
        content = self._extract_content_and_styles(doc_path)[-1]
        prompt = self.prompt_template.format(
            criteria=self._format_criteria(criteria),
            content=content,
            requirements="\n".join(requirements),
            summary="\n".join(summary)
        )
        author = self._extract_author_from_content(content)
        
        response = self.llm.invoke([{"role": "user", "content": prompt}])
        return self._parse_results(response.content, author)

    def _extract_content_and_styles(self, doc_path):
        try:
            if not os.path.exists(doc_path):
                raise FileNotFoundError(f"Файл не найден: {doc_path}")
            
            doc = docx.Document(doc_path)
            content = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            styles = self._extract_styles_from_xml(doc_path)
            
            return content, styles.strip()
            
        except Exception as e:
            raise RuntimeError(f"Ошибка обработки документа: {str(e)}") from e

    def _extract_styles_from_xml(self, doc_path):
        styles_info = []
        try:
            with zipfile.ZipFile(doc_path, 'r') as docx_zip:
                with docx_zip.open('word/document.xml') as doc_file:
                    tree = ET.parse(doc_file)
                    root = tree.getroot()
                    ns = {'w': "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    
                    for para in root.findall('.//w:p', namespaces=ns):
                        style_info = []
                        text = ''.join(node.text for node in para.findall('.//w:t', namespaces=ns) if node.text)
                        if text:
                            style_info.append(f"Текст: {text}")
                        
                        pPr = para.find('.//w:pPr', namespaces=ns)
                        if pPr is not None:
                            alignment = pPr.find('.//w:jc', namespaces=ns)
                            if alignment is not None:
                                style_info.append(f"Выравнивание: {alignment.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')}")
                        
                        rPr = para.find('.//w:r/w:rPr', namespaces=ns)
                        if rPr is not None:
                            font = rPr.find('.//w:rFonts', namespaces=ns)
                            size = rPr.find('.//w:sz', namespaces=ns)
                            if font is not None:
                                style_info.append(f"Шрифт: {font.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii')}")
                            if size is not None:
                                style_info.append(f"Размер: {int(size.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')) / 2}")
                        
                        if style_info:
                            styles_info.append(" | ".join(style_info))
        except Exception as e:
            styles_info.append(f"Ошибка чтения XML: {str(e)}")
        
        return "\n".join(styles_info)

    def _format_criteria(self, criteria):
        formatted_criteria = []
        if isinstance(criteria, dict):
            for i, (criterion, score) in enumerate(zip(criteria['criteria'], criteria['score'])):
                formatted_criteria.append({
                    "criteria": criterion,
                    "score": score
                })
        elif isinstance(criteria, list):
            formatted_criteria = criteria
        
        return "\n".join([
            f"{i+1}. {item['criteria']} ({item['score']} баллов)"
            for i, item in enumerate(formatted_criteria)
        ])
    

    def _parse_results(self, text, author):
        results = []
        lines = text.split('###')
        
        print(lines)
        for block in lines[1:]:
            if not block.strip():
                continue
                
            parts = block.split('\n')
            criteria = parts[0].replace('Критерий:', '').strip()
            score = 0.0
            comment = []
            print(parts)
            for line in parts[1:]:
                line = line.strip()
                print('&', line)
                if line.startswith('Штраф:'):
                    continue
                if line.startswith('Итоговый балл:'):
                    score = float(line.split(':')[-1].split('/')[0].strip())
                elif line.startswith('Комментарий к оценке:'):
                    comment.append(line.split(':', 1)[-1].strip())
                elif line.startswith('-'):
                    comment.append(line[1:].strip())
            
            results.append({
                "criteria": criteria,
                "score": score,
                "comment": '\n'.join(comment)
            })
        print(results)
        return {"status": "success", "results": results, "author": author}



def initialize_evaluator():
    if "GIGACHAT_CREDENTIALS" not in os.environ:
        os.environ["GIGACHAT_CREDENTIALS"] = "Y2ZiMDNkNTEtNGZhMC00ODc5LTk5ZDEtNmJmYjNmMzgyNDljOmIyMjllMjVmLTA5MmYtNGU4OC05NWU1LTFkMmE3OWQ2ZTliOQ=="
    
    return ReportEvaluator(
        GigaChat(
            credentials="Y2ZiMDNkNTEtNGZhMC00ODc5LTk5ZDEtNmJmYjNmMzgyNDljOmIyMjllMjVmLTA5MmYtNGU4OC05NWU1LTFkMmE3OWQ2ZTliOQ==",
            verify_ssl_certs=False,
            scope="GIGACHAT_API_PERS",
            temperature=0.5,
            max_tokens=2000
        )
    )


