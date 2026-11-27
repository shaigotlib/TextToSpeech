# היכן וכיצד להוריד ולהתקין את כלי ההקראה הקולית (Read Aloud Desktop Utility)

כלי קל ומהיר הפועל ברקע ב-Windows ומקריא בקול כל טקסט שמסמנים בכל תוכנה במחשב בלחיצה על **`Ctrl + Alt + R`**.

---

## 🔗 קישורי הורדה מהמאגר

- **מאגר הפרויקט הציבורי ב-GitHub**: [https://github.com/shaigotlib/TextToSpeech](https://github.com/shaigotlib/TextToSpeech)
- **קישור ישיר להורדת קובץ ZIP**: [https://github.com/shaigotlib/TextToSpeech/archive/refs/heads/master.zip](https://github.com/shaigotlib/TextToSpeech/archive/refs/heads/master.zip)

---

## ⚡ התקנה סופר-מהירה (פקודה אחת ב-PowerShell)

פתחו את חלון **PowerShell** (לחצו על `Win + X` ובחרו **Terminal** או **PowerShell**) והדביקו את הפקודה הבאה:

```powershell
git clone https://github.com/shaigotlib/TextToSpeech.git "$HOME\TextToSpeech"; & "$HOME\TextToSpeech\install.bat"
```

תהליך ההתקנה מבצע באופן אוטומטי:
1. בדיקה האם מותקן Python 3.10+ (ובקשת אישור להתקנתו אם אינו קיים).
2. בדיקת ספריות נדרשות (`pywin32`, `edge-tts`) ובקשת אישור מהמשתמש לפני הורדתן.
3. פריסה והתקנה אוטומטית של הכלי בנתיב האפליקציות הסטנדרטי ב-Windows‏ (`%LOCALAPPDATA%\ReadAloudTTS`).
4. הגדרת הפעלה אוטומטית בעליית המחשב / כניסה למערכת (תיקיית Startup ו-Registry).
5. הפעלת הכלי ברקע בשקט (סמל הכלי יופיע במגש המערכת ליד השעון).

---

## 🛠️ אפשרויות התקנה ידנית צעד-אחר-צעד

### אפשרות א': באמצעות Git
1. פתחו את PowerShell ושבטו את המאגר:
   ```powershell
   git clone https://github.com/shaigotlib/TextToSpeech.git
   cd TextToSpeech
   ```
2. לחצו לחיצה כפולה על **`install.bat`** (או הריצו `.\install.ps1` ב-PowerShell).

### אפשרות ב': הורדת קובץ ZIP (ללא צורך ב-Git)
1. היכנסו לכתובת: [https://github.com/shaigotlib/TextToSpeech](https://github.com/shaigotlib/TextToSpeech).
2. לחצו על הכפתור הירוק **Code** ובחרו **Download ZIP**.
3. חלצו את קובץ ה-ZIP שהורדתם לתיקייה במחשב.
4. היכנסו לתיקייה שחולצה ולחצו לחיצה כפולה על הקובץ **`install.bat`**.

---

## 🎧 קיצורי מקשים עיקריים

| קיצור מקשים | פעולה |
| :--- | :--- |
| **`Ctrl + Alt + R`** | **הקראת הטקסט המסומן** / **עצירה מידית** של ההקראה |
| **`Ctrl + Alt + Space`** | **השהיה (Pause) / המשך (Resume)** |
| **`Ctrl + Alt + Up`** | **הגברת מהירות הדיבור** (+1) |
| **`Ctrl + Alt + Down`** | **האטת מהירות הדיבור** (-1) |
| **`Ctrl + Alt + Right`** | דילוג מילה אחת קדימה (פעיל בזמן הקראה) |
| **`Ctrl + Alt + Left`** | חזרה מילה אחת אחורה והקראתה מחדש (פעיל בזמן הקראה) |
| **`Ctrl + Alt + \`** | **מצב העברת קיצורים (Passthrough)** - מעביר את הקיצורים לתוכנה הפעילה |

---

## 🏃 הפעלה, עצירה והסרה

- **הפעלה ידנית**: לחיצה כפולה על `start.bat` (או הרצת `pythonw main.pyw`).
- **עצירת הריצה הנוכחית**: לחיצה כפולה על `stop.bat` (משאיר את ההפעלה האוטומטית לאחר אתחול).
- **הסרה מלאה ונקייה**: לחיצה כפולה על `uninstall.bat` (עוצר את התהליך, מוחק את קיצור ההפעלה האוטומטית, ומנקה את תיקיית `%LOCALAPPDATA%\ReadAloudTTS`).

---

## ⚖️ רישיון ופטור מאחריות

תוכנה זו ניתנת **בחינם לחלוטין לשימוש שאינו מסחרי בלבד**. חל איסור מוחלט לגבות כסף, למכור, או לגבות תשלום עבור שימוש בקוד זה או בנגזרות שלו. התוכנה ניתנת **"כפי שהיא" (AS IS) ללא כל אחריות מכל סוג שהוא**; היוצר אינו נושא בכל אחריות לכל נזק, תוצאה או תקלה שייגרמו כתוצאה מהשימוש בכלי. כל המשתמש בכלי עושה זאת על אחריותו הבלעדית. פרטים מלאים בקובץ `LICENSE`.
