# -*- coding: utf-8 -*-
"""
المسح الميدانيّ الخدميّ - سلمية
Offline street-segment survey app. Runs identically on Windows (desktop)
and Android (via Buildozer build). All data stored locally in SQLite;
export/import via CSV + JSON for merging multiple surveyors' devices.
"""
import os
import csv
import json
import sqlite3
import uuid
from datetime import date

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.metrics import dp

# ---------------------------------------------------------------------------
# Arabic shaping (Kivy does not reshape/bidi Arabic text on its own)
# ---------------------------------------------------------------------------
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def ar(text):
        if not text:
            return text
        return get_display(arabic_reshaper.reshape(text))
except ImportError:
    def ar(text):
        return text  # falls back to raw (disconnected) glyphs if libs missing

# Put an Arabic-capable .ttf next to this file (see README) and it will be
# picked up automatically. Falls back to Kivy's default font otherwise
# (Arabic will not render at all without a matching font).
FONT_CANDIDATES = ["NotoNaskhArabic-Regular.ttf", "Amiri-Regular.ttf", "arabic_font.ttf"]
FONT_NAME = "Roboto"
for fpath in FONT_CANDIDATES:
    if os.path.exists(fpath):
        LabelBase.register(name="Arabic", fn_regular=fpath)
        FONT_NAME = "Arabic"
        break

# ---------------------------------------------------------------------------
# Field configuration - identical set/order to the Data sheet columns A..AQ
# ---------------------------------------------------------------------------
RATE5 = ['جيد جداً', 'جيد', 'متوسط', 'سيئ', 'سيئ جداً']

GROUPS = [
    ("معلومات تعريفية / GIS", [
        ("serial", "المتسلسل", "text"),
        ("sector", "القطَّاع", "text"),
        ("neighborhood", "الحيّ", "text"),
        ("start_point", "نقطة البداية", "text"),
        ("end_point", "نقطة النهاية", "text"),
        ("street_number", "رقم الشارع", "text"),
        ("street_type", "نوع الشارع", "select", ['رئيسيّ', 'ثانويّ', 'سكنيّ', 'تجاريّ', 'مختلط']),
        ("survey_date", "تاريخ المسح", "text"),
        ("gps", "إحداثيات GPS (نقطة البداية)", "gps"),
        ("photo", "الصورة (رابط/رقم)", "text"),
        ("sensitivity", "حساسية الموقع", "select", ['عالي', 'متوسط', 'منخفض']),
        ("sensitivity_reason", "سبب الحساسية", "select",
         ['مدرسة', 'مشفى', 'سوق', 'مركز حكومي', 'معلم تاريخي', 'ساحة عامة', 'مسجد', 'منطقة سياحية', 'أخرى']),
        ("traffic", "كثافة الحركة", "select", ['عالية', 'متوسطة', 'منخفضة']),
    ]),
    ("مؤشرات البنية التحتية", [
        ("pavement_condition", "حالة الرصف", "select", RATE5),
        ("damaged_asphalt_area", "مساحة الاسفلت المتضررة (م٢)", "text"),
        ("sidewalk_condition", "حالة الأرصفة", "select", RATE5),
        ("damaged_sidewalk_length", "طول الأرصفة المتضررة (م)", "text"),
        ("lighting_quality", "جودة الإنارة", "select", RATE5),
    ]),
    ("مؤشرات الهوية البصرية والفن العام", [
        ("visual_aesthetics", "الجمالية البصرية", "select", RATE5),
        ("facade_condition", "حالة الواجهات", "select", RATE5),
        ("signage_condition", "حالة الإعلانات", "select", RATE5),
        ("murals_art", "الجداريات والفن العام", "select", RATE5),
        ("decorative_lighting", "الإنارة الجمالية", "select", RATE5),
    ]),
    ("مؤشرات النظافة", [
        ("street_cleanliness", "نظافة الشارع", "select", RATE5),
        ("containers_available", "عدد الحاويات المتوفرة", "text"),
        ("containers_240_needed", "الحاويات 240 لتر المطلوبة", "text"),
        ("large_containers_needed", "الحاويات الكبيرة المطلوبة", "text"),
    ]),
    ("المؤشرات الحضرية", [
        ("air_quality", "جودة الهواء والروائح", "select", RATE5),
        ("construction_waste", "مخلفات بناء ونفايات", "select", ['يوجد كثيرا', 'يوجد قليلا', 'لا يوجد']),
        ("pedestrian_safety", "سلامة المشاة", "select", RATE5),
        ("accessibility", "إمكانية الوصول", "select", RATE5),
        ("quietness", "الهدوء وقلة الضوضاء", "select", RATE5),
        ("night_safety", "الأمان الليلي", "select", RATE5),
        ("bike_paths", "مسارات الدراجات", "select", RATE5),
    ]),
    ("المساحات الخضراء", [
        ("tree_density", "كثافة الأشجار", "select", RATE5),
        ("tree_quality", "جودة التشجير", "select", RATE5),
        ("irrigation", "الري", "select", RATE5),
        ("shade", "الظلال", "select", RATE5),
        ("gardens", "الحدائق", "select", RATE5),
        ("plazas", "الساحات والدورات", "select", RATE5),
    ]),
    ("الخلاصة", [
        ("priority", "أولوية التدخل", "select", ['عالية', 'متوسطة', 'منخفضة']),
        ("notes", "ملاحظات إضافية", "multiline"),
        ("surveyor_name", "أسم المساح", "text"),
    ]),
]
ALL_FIELDS = [f for _, fields in GROUPS for f in fields]  # (key, label, type, [opts])
FIELD_KEYS = [f[0] for f in ALL_FIELDS]
FIELD_LABELS = [f[1] for f in ALL_FIELDS]

DB_FILENAME = "salamieh_survey.db"


# ---------------------------------------------------------------------------
# Storage layer
# ---------------------------------------------------------------------------
class Store:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        cols = ", ".join(f'"{k}" TEXT' for k in FIELD_KEYS)
        self.conn.execute(
            f'CREATE TABLE IF NOT EXISTS segments (id TEXT PRIMARY KEY, saved_at TEXT, {cols})'
        )
        self.conn.commit()

    def all(self):
        cur = self.conn.execute("SELECT id, saved_at, " + ", ".join(FIELD_KEYS) + " FROM segments ORDER BY saved_at")
        rows = []
        for row in cur.fetchall():
            rec = {"id": row[0], "saved_at": row[1]}
            for i, k in enumerate(FIELD_KEYS):
                rec[k] = row[2 + i]
            rows.append(rec)
        return rows

    def upsert(self, rec):
        keys = ["id", "saved_at"] + FIELD_KEYS
        placeholders = ", ".join("?" for _ in keys)
        cols = ", ".join(f'"{k}"' for k in keys)
        values = [rec.get(k, "") for k in keys]
        self.conn.execute(f"INSERT OR REPLACE INTO segments ({cols}) VALUES ({placeholders})", values)
        self.conn.commit()

    def delete(self, seg_id):
        self.conn.execute("DELETE FROM segments WHERE id=?", (seg_id,))
        self.conn.commit()

    def exists(self, seg_id):
        cur = self.conn.execute("SELECT 1 FROM segments WHERE id=?", (seg_id,))
        return cur.fetchone() is not None


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def info_popup(title, message):
    box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
    box.add_widget(Label(text=ar(message), font_name=FONT_NAME, halign="right"))
    btn = Button(text=ar("حسناً"), size_hint_y=None, height=dp(44))
    box.add_widget(btn)
    popup = Popup(title=ar(title), content=box, size_hint=(0.85, 0.5))
    btn.bind(on_release=popup.dismiss)
    popup.open()


def confirm_popup(title, message, on_yes):
    box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
    box.add_widget(Label(text=ar(message), font_name=FONT_NAME))
    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    yes = Button(text=ar("نعم"))
    no = Button(text=ar("إلغاء"))
    row.add_widget(yes)
    row.add_widget(no)
    box.add_widget(row)
    popup = Popup(title=ar(title), content=box, size_hint=(0.85, 0.4))
    yes.bind(on_release=lambda *a: (on_yes(), popup.dismiss()))
    no.bind(on_release=popup.dismiss)
    popup.open()


# ---------------------------------------------------------------------------
# Form screen
# ---------------------------------------------------------------------------
class FormScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.editing_id = None
        self.inputs = {}
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")

        header = Label(text=ar("المسح الميدانيّ الخدميّ لمدينة سلمية"), font_name=FONT_NAME,
                        size_hint_y=None, height=dp(44), bold=True)
        root.add_widget(header)

        scroll = ScrollView()
        col = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=dp(10))
        col.bind(minimum_height=col.setter("height"))

        for group_title, fields in GROUPS:
            gl = Label(text=ar(group_title), font_name=FONT_NAME, bold=True,
                       size_hint_y=None, height=dp(34), color=(0.18, 0.36, 0.30, 1))
            col.add_widget(gl)
            for f in fields:
                key, label, ftype = f[0], f[1], f[2]
                opts = f[3] if len(f) > 3 else None
                col.add_widget(Label(text=ar(label), font_name=FONT_NAME,
                                      size_hint_y=None, height=dp(26), halign="right"))
                if ftype == "select":
                    w = Spinner(text="", values=opts, size_hint_y=None, height=dp(42), font_name=FONT_NAME)
                elif ftype == "multiline":
                    w = TextInput(size_hint_y=None, height=dp(80), font_name=FONT_NAME, multiline=True)
                elif ftype == "gps":
                    row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(78), spacing=dp(4))
                    w = TextInput(size_hint_y=None, height=dp(42), font_name=FONT_NAME,
                                  hint_text="خط العرض, خط الطول")
                    gbtn = Button(text=ar("تحديد الموقع الحالي"), size_hint_y=None, height=dp(32),
                                  font_name=FONT_NAME)
                    gbtn.bind(on_release=lambda inst, w=w: self._capture_gps(w))
                    row.add_widget(w)
                    row.add_widget(gbtn)
                    col.add_widget(row)
                    self.inputs[key] = w
                    continue
                else:
                    w = TextInput(size_hint_y=None, height=dp(42), font_name=FONT_NAME)
                col.add_widget(w)
                self.inputs[key] = w

        scroll.add_widget(col)
        root.add_widget(scroll)

        actions = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8), padding=dp(8))
        self.save_btn = Button(text=ar("حفظ المقطع"), font_name=FONT_NAME)
        clear_btn = Button(text=ar("تفريغ"), font_name=FONT_NAME)
        self.save_btn.bind(on_release=lambda *a: self._save())
        clear_btn.bind(on_release=lambda *a: self.reset())
        actions.add_widget(self.save_btn)
        actions.add_widget(clear_btn)
        root.add_widget(actions)

        self.add_widget(root)
        self.inputs["survey_date"].text = date.today().isoformat()

    def _capture_gps(self, widget):
        try:
            from plyer import gps

            def on_location(**kwargs):
                lat = kwargs.get("lat")
                lon = kwargs.get("lon")
                widget.text = f"{lat:.6f}, {lon:.6f}"
                gps.stop()

            gps.configure(on_location=on_location)
            gps.start(minTime=1000, minDistance=0)
        except NotImplementedError:
            info_popup("غير متاح", "تحديد الموقع عبر GPS غير مدعوم على سطح المكتب - الرجاء إدخال الإحداثيات يدويًا.")
        except Exception as e:
            info_popup("تعذّر تحديد الموقع", str(e))

    def load_record(self, rec):
        self.editing_id = rec["id"]
        for k, w in self.inputs.items():
            w.text = rec.get(k, "") or ""
        self.save_btn.text = ar("حفظ التعديل")

    def reset(self):
        keep_name = self.inputs["surveyor_name"].text
        keep_date = self.inputs["survey_date"].text
        for w in self.inputs.values():
            w.text = ""
        self.inputs["surveyor_name"].text = keep_name
        self.inputs["survey_date"].text = keep_date or date.today().isoformat()
        self.editing_id = None
        self.save_btn.text = ar("حفظ المقطع")

    def _save(self):
        rec = {k: w.text for k, w in self.inputs.items()}
        if self.editing_id:
            rec["id"] = self.editing_id
        else:
            rec["id"] = "seg_" + uuid.uuid4().hex[:12]
        rec["saved_at"] = __import__("datetime").datetime.now().isoformat()
        self.app.store.upsert(rec)
        info_popup("تم الحفظ", "تم حفظ المقطع على هذا الجهاز.")
        self.reset()
        self.app.list_screen.refresh()


# ---------------------------------------------------------------------------
# List screen
# ---------------------------------------------------------------------------
class ListScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        root = BoxLayout(orientation="vertical")

        toolbar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6), padding=dp(6))
        b1 = Button(text=ar("تصدير CSV"), font_name=FONT_NAME)
        b2 = Button(text=ar("تصدير JSON"), font_name=FONT_NAME)
        b3 = Button(text=ar("استيراد/دمج JSON"), font_name=FONT_NAME)
        b1.bind(on_release=lambda *a: self.export_csv())
        b2.bind(on_release=lambda *a: self.export_json())
        b3.bind(on_release=lambda *a: self.import_json_dialog())
        toolbar.add_widget(b1)
        toolbar.add_widget(b2)
        toolbar.add_widget(b3)
        root.add_widget(toolbar)

        self.count_label = Label(text="", font_name=FONT_NAME, size_hint_y=None, height=dp(26))
        root.add_widget(self.count_label)

        self.scroll = ScrollView()
        self.col = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=dp(8))
        self.col.bind(minimum_height=self.col.setter("height"))
        self.scroll.add_widget(self.col)
        root.add_widget(self.scroll)

        self.add_widget(root)

    def on_pre_enter(self, *a):
        self.refresh()

    def refresh(self):
        self.col.clear_widgets()
        records = self.app.store.all()
        self.count_label.text = ar(f"{len(records)} مقطع محفوظ")
        for rec in records:
            row = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(6))
            desc = f"#{rec.get('serial','-')} — {rec.get('neighborhood','')} ({rec.get('start_point','')} → {rec.get('end_point','')})\n{rec.get('street_type','')} · {rec.get('survey_date','')}"
            row.add_widget(Label(text=ar(desc), font_name=FONT_NAME, halign="right"))
            edit_btn = Button(text=ar("تعديل"), size_hint_x=None, width=dp(80), font_name=FONT_NAME)
            del_btn = Button(text=ar("حذف"), size_hint_x=None, width=dp(70), font_name=FONT_NAME)
            edit_btn.bind(on_release=lambda inst, r=rec: self._edit(r))
            del_btn.bind(on_release=lambda inst, r=rec: self._delete(r))
            row.add_widget(edit_btn)
            row.add_widget(del_btn)
            self.col.add_widget(row)

    def _edit(self, rec):
        self.app.form_screen.load_record(rec)
        self.app.sm.current = "form"

    def _delete(self, rec):
        def do_delete():
            self.app.store.delete(rec["id"])
            self.refresh()
        confirm_popup("تأكيد", "حذف هذا المقطع؟", do_delete)

    def _export_dir(self):
        d = self.app.user_data_dir
        os.makedirs(d, exist_ok=True)
        return d

    def export_csv(self):
        records = self.app.store.all()
        if not records:
            info_popup("لا توجد بيانات", "لا توجد مقاطع محفوظة للتصدير.")
            return
        path = os.path.join(self._export_dir(), f"salamieh_survey_{int(__import__('time').time())}.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(FIELD_LABELS)
            for rec in records:
                w.writerow([rec.get(k, "") for k in FIELD_KEYS])
        info_popup("تم التصدير", f"تم الحفظ في:\n{path}")

    def export_json(self):
        records = self.app.store.all()
        if not records:
            info_popup("لا توجد بيانات", "لا توجد مقاطع محفوظة للتصدير.")
            return
        path = os.path.join(self._export_dir(), f"salamieh_survey_{int(__import__('time').time())}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        info_popup("تم التصدير", f"تم الحفظ في:\n{path}")

    def import_json_dialog(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        chooser = FileChooserListView(path=self._export_dir(), filters=["*.json"])
        box.add_widget(chooser)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        ok = Button(text=ar("دمج"))
        cancel = Button(text=ar("إلغاء"))
        row.add_widget(ok)
        row.add_widget(cancel)
        box.add_widget(row)
        popup = Popup(title=ar("اختر ملف JSON للدمج"), content=box, size_hint=(0.95, 0.9))

        def do_import(*a):
            if not chooser.selection:
                return
            self._merge_file(chooser.selection[0])
            popup.dismiss()

        ok.bind(on_release=do_import)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _merge_file(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                incoming = json.load(f)
            added = 0
            for rec in incoming:
                if not self.app.store.exists(rec.get("id", "")):
                    self.app.store.upsert(rec)
                    added += 1
            self.refresh()
            info_popup("تم الدمج", f"تمت إضافة {added} مقطع جديد.")
        except Exception as e:
            info_popup("خطأ", f"تعذّر قراءة الملف: {e}")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class SurveyApp(App):
    def build(self):
        self.title = "المسح الميدانيّ الخدميّ - سلمية"
        os.makedirs(self.user_data_dir, exist_ok=True)
        db_path = os.path.join(self.user_data_dir, DB_FILENAME)
        self.store = Store(db_path)

        self.sm = ScreenManager()
        self.form_screen = FormScreen(self, name="form")
        self.list_screen = ListScreen(self, name="list")
        self.sm.add_widget(self.form_screen)
        self.sm.add_widget(self.list_screen)

        root = BoxLayout(orientation="vertical")
        tabs = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(4), padding=dp(4))
        t1 = Button(text=ar("إدخال مقطع جديد"), font_name=FONT_NAME)
        t2 = Button(text=ar("المقاطع المحفوظة"), font_name=FONT_NAME)
        t1.bind(on_release=lambda *a: setattr(self.sm, "current", "form"))
        t2.bind(on_release=lambda *a: setattr(self.sm, "current", "list"))
        tabs.add_widget(t1)
        tabs.add_widget(t2)
        root.add_widget(tabs)
        root.add_widget(self.sm)
        return root


if __name__ == "__main__":
    SurveyApp().run()
