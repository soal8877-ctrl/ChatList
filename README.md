# ChatList
программа на Python

## Установка зависимостей

```bash
pip install -r requirements.txt
```

Если возникают проблемы с плагинами Qt на Windows, попробуйте переустановить PyQt5:

```bash
pip uninstall PyQt5
pip install PyQt5
```

Или используйте альтернативу PySide2:

```bash
pip install PySide2
python main_pyside.py
```

## Запуск приложения

```bash
python main.py
```

Или с PySide2:

```bash
python main_pyside.py
```

## Описание

Минимальное приложение на PyQt5 с графическим интерфейсом:
- Окно с заголовком
- Метка с текстом
- Кнопка, которая изменяет текст метки при нажатии