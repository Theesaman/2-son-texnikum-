#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KARMANA TUMAN 2-SON TEXNIKUMI — PREMIUM TELEGRAM BOT + WEB SERVER
=================================================================
Ushbu dastur bir vaqtning o'zida:
1. Veb-saytni (`index.html` / `karmana_2_texnikum.html`) va REST API (`/api/apply`, `/api/stats`) ni FastAPI orqali ishga tushiradi.
2. Ko'p tilli (O'zbek, Rus, Ingliz) Premium Telegram Botni (`aiogram 3.x`) ishga tushiradi:
   - /start komandasi va til tanlash (UZ / RU / EN)
   - Saytdan deep-link (`/start apply_30610403`) orqali kelgan arizalarni avtomatik qabul qilish
   - 7 ta rasmiy kasbiy yo'nalish va barcha kvalifikatsiyalar katalogi
   - Bosqichma-bosqich (FSM) onlayn ariza topshirish (Ism-sharif, Telefon kontakt tugmasi, Yo'nalish, Ta'lim shakli, Izoh)
   - SQLite ma'lumotlar bazasi (`texnikum_data.db`) da barcha arizalar va foydalanuvchilarni saqlash
   - Admin panel (`/admin`) — Statistika, barcha arizalarni CSV (Excel) formatida yuklab olish, barcha foydalanuvchilarga e'lon yuborish (Broadcast), yangi ariza tushganda Admin Telegramiga tezkor bildirishnoma yuborish.
"""

import asyncio
import csv
import io
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)

# ---------------------------------------------------------------------------
# KONFIGURATSIYA (ENVIRONMENT VARIABLES)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("karmana_2_texnikum")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {
    int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()
}
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://karmana2texnikum.up.railway.app").rstrip("/")
PORT = int(os.getenv("PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", "texnikum_data.db")
BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 7 TA RASMIY KASB YO'NALISHI VA KVALIFIKATSIYALAR BAZASI
# ---------------------------------------------------------------------------
PROGRAMS = {
    "30610403": {
        "code": "30610403",
        "icon": "💻",
        "duration": "2 yil",
        "form": "Dual ta'lim / Kunduzgi",
        "title": {
            "uz": "Kompyuter tarmoqlari va IT-servis",
            "ru": "Компьютерные сети и IT-сервис",
            "en": "Computer Networks & IT Service",
        },
        "quals": {
            "uz": [
                "Kompyuter tarmoqlari administratori va montajchisi",
                "Kompyuter va ofis texnikalariga texnik xizmat ko'rsatish ustasi",
                "IT-servis va dasturiy-apparat vositalarini sozlash mutaxassisi",
            ],
            "ru": [
                "Администратор и монтажник компьютерных сетей",
                "Мастер по обслуживанию компьютерной и офисной техники",
                "Специалист по IT-сервису и настройке систем",
            ],
            "en": [
                "Computer Network Administrator & Installer",
                "Computer & Office Equipment Maintenance Technician",
                "IT Service & Hardware/Software Configuration Specialist",
            ],
        },
    },
    "30711605": {
        "code": "30711605",
        "icon": "🚗",
        "duration": "2 yil",
        "form": "Dual ta'lim / Kunduzgi",
        "title": {
            "uz": "Avtomobillar servisi",
            "ru": "Автомобильный сервис",
            "en": "Automotive Service & Diagnostics",
        },
        "quals": {
            "uz": [
                "1. Avtomobil dvigatellarini tashxislash va ta'mirlash chilangari",
                "2. Avtomobil shassisiga texnik xizmat ko'rsatish va ta'mirlash chilangari",
                "3. Avtomobil kuzovini ta'mirlash chilangari",
                "4. Avtomobil elektr va elektron jihozlariga texnik xizmat ko'rsatish bo'yicha elektrchilangar",
                "5. Avtomobillarni avtotuning qilish bo'yicha chilangar",
                '6. "B" yoki "BC" toifali avtomobil haydovchisi',
            ],
            "ru": [
                "1. Слесарь по диагностике и ремонту автомобильных двигателей",
                "2. Слесарь по техобслуживанию и ремонту шасси автомобиля",
                "3. Слесарь по кузовному ремонту автомобилей",
                "4. Электрослесарь по обслуживанию электрооборудования автомобилей",
                "5. Слесарь по автотюнингу автомобилей",
                "6. Водитель автомобиля категории «B» или «BC»",
            ],
            "en": [
                "1. Automotive Engine Diagnostics & Repair Mechanic",
                "2. Automotive Chassis Maintenance & Repair Mechanic",
                "3. Automotive Body Repair Specialist",
                "4. Automotive Electrical & Electronic Systems Technician",
                "5. Car Tuning & Modification Specialist",
                '6. Category "B" or "BC" Motor Vehicle Driver',
            ],
        },
    },
    "30720436": {
        "code": "30720436",
        "icon": "👗",
        "duration": "2 yil",
        "form": "Dual ta'lim / Kunduzgi",
        "title": {
            "uz": "Moda va tikuv ishlab chiqarish texnologiyasi",
            "ru": "Мода и технология швейного производства",
            "en": "Fashion & Garment Manufacturing Technology",
        },
        "quals": {
            "uz": [
                "1. Tikuvchi",
                "2. Konstruktor bichuvchi",
                "3. 3D modelyer",
                "4. Sifat nazoratchisi",
                "5. Moda illyustratori va kiyim dizayneri",
            ],
            "ru": [
                "1. Швея / Портной",
                "2. Конструктор-закройщик",
                "3. 3D-модельер одежды",
                "4. Контролер качества",
                "5. Фэшн-иллюстратор и дизайнер одежды",
            ],
            "en": [
                "1. Garment Tailor / Seamstress",
                "2. Pattern Maker & Cutter",
                "3. 3D Apparel Modeler",
                "4. Quality Control Inspector",
                "5. Fashion Illustrator & Clothing Designer",
            ],
        },
    },
    "30710105": {
        "code": "30710105",
        "icon": "🧪",
        "duration": "2 yil",
        "form": "Dual ta'lim / Kunduzgi",
        "title": {
            "uz": "Kimyoviy tolalar ishlab chiqarish operatori",
            "ru": "Оператор производства химических волокон",
            "en": "Chemical Fiber Production Operator",
        },
        "quals": {
            "uz": [
                "1. Eshish va cho'zish operatori",
                "2. Kimyoviy tolalarni eshish va o'rash operatori",
                "3. Kimyoviy tolalarni pardozlovchi",
            ],
            "ru": [
                "1. Оператор кручения и вытяжки",
                "2. Оператор кручения и намотки химических волокон",
                "3. Отделочник химических волокон",
            ],
            "en": [
                "1. Twisting & Drawing Operator",
                "2. Chemical Fiber Twisting & Winding Operator",
                "3. Chemical Fiber Finishing Specialist",
            ],
        },
    },
    "30710310": {
        "code": "30710310",
        "icon": "⚡",
        "duration": "2 yil",
        "form": "Dual ta'lim / Kunduzgi",
        "title": {
            "uz": "Elektromontyor",
            "ru": "Электромонтёр",
            "en": "Industrial & Power Electrician",
        },
        "quals": {
            "uz": [
                "1. Elektromontyor (sanoat va fuqaro obyektlari elektr jihozlarini o'rnatish hamda xizmat ko'rsatish)"
            ],
            "ru": [
                "1. Электромонтёр по монтажу, обслуживанию и ремонту электрооборудования"
            ],
            "en": [
                "1. Certified Electrician (Installation, Maintenance & Repair of Electrical Systems)"
            ],
        },
    },
    "30810105": {
        "code": "30810105",
        "icon": "🚜",
        "duration": "2 yil",
        "form": "Dual ta'lim / Kunduzgi",
        "title": {
            "uz": "Traktor va agrotexnikalar mashinisti",
            "ru": "Машинист тракторов и агротехники",
            "en": "Tractor & Agricultural Machinery Operator",
        },
        "quals": {
            "uz": [
                "1. Traktorchi-mashinist",
                "2. GPS va auto-steering tizimlari operatori",
                '3. "B" yoki "BC" toifali avtomobil haydovchisi',
            ],
            "ru": [
                "1. Тракторист-машинист",
                "2. Оператор систем GPS и автопилотирования (auto-steering)",
                "3. Водитель автомобиля категории «B» или «BC»",
            ],
            "en": [
                "1. Tractor & Agricultural Machinery Operator",
                "2. GPS & Auto-Steering Precision Farming Operator",
                '3. Category "B" or "BC" Motor Vehicle Driver',
            ],
        },
    },
    "30711307": {
        "code": "30711307",
        "icon": "⚙️",
        "duration": "2 yil",
        "form": "Dual ta'lim / Kunduzgi",
        "title": {
            "uz": "Metallga qayta ishlov berish",
            "ru": "Металлообработка",
            "en": "Metalworking & Precision Machining",
        },
        "quals": {
            "uz": [
                "1. Tokar va metallga mexanik ishlov berish mutaxassisi",
                "2. Frezerlovchi va dastgohlar operatori",
                "3. Sanoat chilangari va metall konstruksiyalarga ishlov beruvchi",
            ],
            "ru": [
                "1. Токарь и специалист по механической обработке металла",
                "2. Фрезеровщик и оператор металлообрабатывающих станков",
                "3. Слесарь механосборочных работ и металлоконструкций",
            ],
            "en": [
                "1. Lathe Operator & Mechanical Metalworking Specialist",
                "2. Milling Machine & CNC Equipment Operator",
                "3. Industrial Fitter & Metal Fabrication Technician",
            ],
        },
    },
}

# ---------------------------------------------------------------------------
# KO'P TILLI LUG'AT (UZ / RU / EN)
# ---------------------------------------------------------------------------
TEXTS = {
    "uz": {
        "welcome": (
            "🏛 <b>Navoiy viloyati, Karmana tumani 2-son texnikumi</b>ning rasmiy Telegram botiga xush kelibsiz!\n\n"
            "🎓 <b>Ta'lim darajasi:</b> Boshlang'ich kasbiy ta'lim (Dual ta'lim dasturi)\n"
            "👥 <b>O'quvchilar soni:</b> ~800 nafar\n"
            "📚 <b>Kasbiy yo'nalishlar:</b> 7 ta zamonaviy mutaxassislik\n\n"
            "Quyidagi menyudan kerakli bo'limni tanlang:"
        ),
        "menu_programs": "📚 7 ta Yo'nalishlar",
        "menu_apply": "📝 Onlayn Ariza Topshirish",
        "menu_dual": "🤝 Dual Ta'lim Dasturi",
        "menu_about": "🏛 Texnikum Haqida",
        "menu_contact": "📍 Manzil va Aloqa",
        "menu_lang": "🌐 Tilni o'zgartirish",
        "choose_program": "📚 <b>Texnikumdagi 7 ta kasbiy yo'nalish:</b>\nBatafsil ma'lumot va kvalifikatsiyalarni ko'rish uchun yo'nalishni tanlang:",
        "apply_this": "✅ Shu yo'nalishga ariza topshirish",
        "back_to_programs": "⬅️ Yo'nalishlar ro'yxatiga qaytish",
        "ask_name": "📝 <b>Onlayn qabul arizasi (1/4)</b>\n\nIltimos, to'liq <b>Ism, Familiya va Sharifingizni</b> kiriting (Masalan: <i>Aliyev Sardor Rustam o'g'li</i>):",
        "ask_phone": "📞 <b>2/4. Telefon raqamingizni yuboring:</b>\n\nPastdagi <b>«📱 Raqamni yuborish»</b> tugmasini bosing yoki raqamingizni <code>+998901234567</code> shaklida yozing:",
        "share_phone_btn": "📱 Raqamni yuborish",
        "cancel_btn": "❌ Bekor qilish",
        "ask_program": "🎓 <b>3/4. Qaysi kasb yo'nalishida o'qimoqchisiz?</b>\nRo'yxatdan tanlang:",
        "ask_note": "💬 <b>4/4. Qo'shimcha savol yoki izohingiz bormi?</b>\n(Masalan: nechanchi sinfni bitirgansiz yoki dual ta'lim bo'yicha savol. Agar yo'q bo'lsa «Yo'q» deb yozing):",
        "app_success": (
            "🎉 <b>Arizangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
            "🆔 <b>Ariza raqami:</b> #{app_id}\n"
            "👤 <b>F.I.Sh:</b> {full_name}\n"
            "📞 <b>Telefon:</b> {phone}\n"
            "🎓 <b>Yo'nalish:</b> {program}\n"
            "📝 <b>Izoh:</b> {note}\n\n"
            "Qabul komissiyamiz tez orada siz bilan bog'lanadi!"
        ),
        "cancelled": "❎ Jarayon bekor qilindi. Asosiy menyudasiz.",
        "dual_info": (
            "🤝 <b>DUAL TA'LIM DASTURI NIMA?</b>\n\n"
            "Karmana tuman 2-son texnikumida <b>Boshlang'ich kasbiy ta'lim darajasi</b>da dual ta'lim yo'lga qo'yilgan:\n"
            "• <b>Nazariya + Amaliyot:</b> O'quvchilar haftaning bir qismini texnikum ustaxonalarida, qolgan qismini esa Navoiy va Karmanadagi yirik korxonalarda o'tkazadilar.\n"
            "• <b>Ko'p kvalifikatsiyali diplom:</b> Bitiruvchilar bitta yo'nalish ichida 6 tagacha amaliy kasb malakasiga va Avtoservis / Traktor yo'nalishlarida <b>«B» yoki «BC» haydovchilik guvohnomasiga</b> ega bo'ladilar.\n"
            "• <b>Ish bilan ta'minlash:</b> O'qish davridayoq korxonalarda tajriba to'plab, bitirgach doimiy ish o'rniga ega bo'lish imkoniyati."
        ),
        "about_info": (
            "🏛 <b>NAVOIY VILOYATI KARMANA TUMANI 2-SON TEXNIKUMI</b>\n\n"
            "📊 <b>Asosiy ko'rsatkichlar:</b>\n"
            "• <b>O'quvchilar kontingenti:</b> ~800 nafar faol o'quvchi\n"
            "• <b>Kasbiy yo'nalishlar:</b> 7 ta rasmiy yo'nalish\n"
            "• <b>Beriladigan malakalar:</b> 20+ ishchi kvalifikatsiyalar\n"
            "• <b>Ta'lim tillari:</b> O'zbek, Rus, Ingliz tili qo'llab-quvvatiruvi\n\n"
            "Texnikum замонавий IT-laboratoriya, avtodiagnostika ustaxonasi, 3D tikuv-dizayn studiyasi, kimyo va elektrotexnika stendlari hamda GPS agrotexnika poligoni bilan jihozlangan."
        ),
        "contact_info": (
            "📍 <b>MANZIL VA ALOQA</b>\n\n"
            "🏢 <b>Manzil:</b> Navoiy viloyati, Karmana tumani, 2-son texnikumi binosi\n"
            "🕘 <b>Qabul vaqti:</b> Dushanba – Shanba (08:30 – 17:30)\n"
            "🌐 <b>Rasmiy veb-sayt:</b> {public_url}\n\n"
            "Savolingiz bo'lsa, <b>«📝 Onlayn Ariza Topshirish»</b> tugmasi orqali ma'lumot qoldiring!"
        ),
    },
    "ru": {
        "welcome": (
            "🏛 Добро пожаловать в официальный Telegram-бот <b>Техникума №2 Карманинского района Навоийской области</b>!\n\n"
            "🎓 <b>Уровень образования:</b> Начальное профессиональное образование (Дуальная программа)\n"
            "👥 <b>Контингент:</b> ~800 учащихся\n"
            "📚 <b>Направления обучения:</b> 7 современных специальностей\n\n"
            "Выберите нужный раздел в меню ниже:"
        ),
        "menu_programs": "📚 7 Направлений",
        "menu_apply": "📝 Подать Онлайн-Заявку",
        "menu_dual": "🤝 Дуальное Обучение",
        "menu_about": "🏛 О Техникуме",
        "menu_contact": "📍 Адрес и Контакты",
        "menu_lang": "🌐 Сменить язык",
        "choose_program": "📚 <b>7 профессиональных направлений техникума:</b>\nВыберите специальность, чтобы увидеть список присваиваемых квалификаций:",
        "apply_this": "✅ Подать заявку на это направление",
        "back_to_programs": "⬅️ Назад к списку направлений",
        "ask_name": "📝 <b>Онлайн-заявка на поступление (1/4)</b>\n\nПожалуйста, введите ваши <b>Фамилию, Имя и Отчество</b>:",
        "ask_phone": "📞 <b>2/4. Отправьте ваш номер телефона:</b>\n\nНажмите кнопку <b>«📱 Отправить номер»</b> ниже или напишите номер в формате <code>+998901234567</code>:",
        "share_phone_btn": "📱 Отправить номер",
        "cancel_btn": "❌ Отмена",
        "ask_program": "🎓 <b>3/4. Выберите направление обучения:</b>",
        "ask_note": "💬 <b>4/4. Есть ли у вас дополнительные вопросы или комментарий?</b>\n(Например, какой класс вы окончили. Если нет, напишите «Нет»):",
        "app_success": (
            "🎉 <b>Ваша заявка успешно принята!</b>\n\n"
            "🆔 <b>Номер заявки:</b> #{app_id}\n"
            "👤 <b>Ф.И.О:</b> {full_name}\n"
            "📞 <b>Телефон:</b> {phone}\n"
            "🎓 <b>Направление:</b> {program}\n"
            "📝 <b>Комментарий:</b> {note}\n\n"
            "Приёмная комиссия свяжется с вами в ближайшее время!"
        ),
        "cancelled": "❎ Действие отменено. Вы в главном меню.",
        "dual_info": (
            "🤝 <b>ПРОГРАММА ДУАЛЬНОГО ОБУЧЕНИЯ</b>\n\n"
            "Во 2-м техникуме Карманинского района действует система дуального образования:\n"
            "• <b>Теория + Практика:</b> Студенты совмещают учёбу в лабораториях техникума с практикой на предприятиях Карманы и Навои.\n"
            "• <b>До 6 квалификаций в дипломе:</b> Включая водительские права категорий <b>«B» или «BC»</b> для направлений Автосервис и Агротехника.\n"
            "• <b>Трудоустройство:</b> Реальный производственный стаж ещё во время учёбы."
        ),
        "about_info": (
            "🏛 <b>ТЕХНИКУМ №2 КАРМАНИНСКОГО РАЙОНА НАВОИЙСКОЙ ОБЛАСТИ</b>\n\n"
            "• <b>Учащихся:</b> ~800 человек\n"
            "• <b>Направлений:</b> 7 государственных специальностей\n"
            "• <b>Квалификаций:</b> более 20 рабочих профессий\n\n"
            "Техникум оснащён компьютерными сетями, автосервисным подъёмником, 3D-студией моды, электромонтажными стендами, токарно-фрезерными станками и тракторами с GPS."
        ),
        "contact_info": (
            "📍 <b>АДРЕС И КОНТАКТЫ</b>\n\n"
            "🏢 <b>Адрес:</b> Навоийская область, Карманинский район, Техникум №2\n"
            "🕘 <b>Часы приёма:</b> Пн – Сб (08:30 – 17:30)\n"
            "🌐 <b>Веб-сайт:</b> {public_url}"
        ),
    },
    "en": {
        "welcome": (
            "🏛 Welcome to the official Telegram Bot of <b>Karmana District Technical College #2 (Navoiy Region)</b>!\n\n"
            "🎓 <b>Education Level:</b> Initial Vocational Education (Dual Program)\n"
            "👥 <b>Students:</b> ~800 enrolled\n"
            "📚 <b>Vocational Tracks:</b> 7 official specialties\n\n"
            "Choose an option from the menu below:"
        ),
        "menu_programs": "📚 7 Vocational Programs",
        "menu_apply": "📝 Apply Online",
        "menu_dual": "🤝 Dual Education Info",
        "menu_about": "🏛 About the College",
        "menu_contact": "📍 Location & Contact",
        "menu_lang": "🌐 Change Language",
        "choose_program": "📚 <b>Our 7 Official Vocational Programs:</b>\nSelect any program below to inspect its qualifications:",
        "apply_this": "✅ Apply for this Program",
        "back_to_programs": "⬅️ Back to Programs List",
        "ask_name": "📝 <b>Online Admission Application (1/4)</b>\n\nPlease enter your <b>Full Name</b>:",
        "ask_phone": "📞 <b>2/4. Share your phone number:</b>\n\nTap <b>«📱 Share Phone Number»</b> below or type it as <code>+998901234567</code>:",
        "share_phone_btn": "📱 Share Phone Number",
        "cancel_btn": "❌ Cancel",
        "ask_program": "🎓 <b>3/4. Select your desired vocational program:</b>",
        "ask_note": "💬 <b>4/4. Any additional notes or questions?</b>\n(Or type «None»):",
        "app_success": (
            "🎉 <b>Your application has been submitted!</b>\n\n"
            "🆔 <b>Application ID:</b> #{app_id}\n"
            "👤 <b>Full Name:</b> {full_name}\n"
            "📞 <b>Phone:</b> {phone}\n"
            "🎓 <b>Program:</b> {program}\n"
            "📝 <b>Note:</b> {note}\n\n"
            "Our admissions team will contact you shortly!"
        ),
        "cancelled": "❎ Application cancelled. Returned to main menu.",
        "dual_info": (
            "🤝 <b>DUAL EDUCATION PROGRAM</b>\n\n"
            "• <b>Theory + Industry Practice:</b> Students split their week between college labs and leading industrial enterprises in Karmana & Navoiy.\n"
            '• <b>Multi-Qualification Diploma:</b> Earn up to 6 technical qualifications plus a Category "B" or "BC" driver license in Automotive & Tractor tracks.'
        ),
        "about_info": (
            "🏛 <b>KARMANA DISTRICT TECHNICAL COLLEGE #2 (NAVOIY REGION)</b>\n\n"
            "• <b>Active Students:</b> ~800\n"
            "• <b>Official Programs:</b> 7 Vocational Tracks\n"
            "• <b>Certified Qualifications:</b> 20+ specialized career roles"
        ),
        "contact_info": (
            "📍 <b>LOCATION & CONTACT</b>\n\n"
            "🏢 <b>Address:</b> Karmana District, Navoiy Region, Technical College #2\n"
            "🕘 <b>Hours:</b> Mon – Sat (08:30 – 17:30)\n"
            "🌐 <b>Website:</b> {public_url}"
        ),
    },
}

# ---------------------------------------------------------------------------
# SQLITE MA'LUMOTLAR BAZASI FUNKSIYALARI
# ---------------------------------------------------------------------------
def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                lang TEXT DEFAULT 'uz',
                joined_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                program_code TEXT NOT NULL,
                program_title TEXT NOT NULL,
                note TEXT,
                source TEXT DEFAULT 'telegram_bot',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def upsert_user(user_id: int, username: str, full_name: str, lang: Optional[str] = None) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, username, full_name, lang, joined_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, username or "", full_name or "", lang or "uz", now),
            )
        else:
            if lang:
                conn.execute(
                    "UPDATE users SET username = ?, full_name = ?, lang = ? WHERE user_id = ?",
                    (username or "", full_name or "", lang, user_id),
                )
            else:
                conn.execute(
                    "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                    (username or "", full_name or "", user_id),
                )
        conn.commit()


def get_user_lang(user_id: int) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] in TEXTS else "uz"


def save_application(
    user_id: int,
    full_name: str,
    phone: str,
    program_code: str,
    program_title: str,
    note: str,
    source: str = "telegram_bot",
) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO applications (user_id, full_name, phone, program_code, program_title, note, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, full_name, phone, program_code, program_title, note, source, now),
        )
        conn.commit()
        return cur.lastrowid or 1


def get_stats() -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        by_prog = conn.execute(
            "SELECT program_code, COUNT(*) FROM applications GROUP BY program_code"
        ).fetchall()
    return {
        "total_users": total_users,
        "total_applications": total_apps,
        "by_program": {code: cnt for code, cnt in by_prog},
    }


def export_applications_csv() -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["ID", "User ID", "F.I.Sh", "Telefon", "Kasb Kodi", "Yo'nalish Nomi", "Izoh", "Manba", "Vaqt"]
    )
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, user_id, full_name, phone, program_code, program_title, note, source, created_at FROM applications ORDER BY id DESC"
        ).fetchall()
        for r in rows:
            writer.writerow(r)
    return output.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------------
# KLAVIATURALAR (REPLY & INLINE KEYBOARDS)
# ---------------------------------------------------------------------------
def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["menu_programs"]), KeyboardButton(text=t["menu_apply"])],
            [KeyboardButton(text=t["menu_dual"]), KeyboardButton(text=t["menu_about"])],
            [KeyboardButton(text=t["menu_contact"]), KeyboardButton(text=t["menu_lang"])],
        ],
        resize_keyboard=True,
    )


def lang_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="setlang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en"),
            ]
        ]
    )


def programs_inline_kb(lang: str, prefix: str = "prog_") -> InlineKeyboardMarkup:
    rows = []
    for code, p in PROGRAMS.items():
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{p['icon']} {code} — {p['title'][lang]}",
                    callback_data=f"{prefix}{code}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def program_detail_kb(code: str, lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["apply_this"], callback_data=f"startapply_{code}")],
            [InlineKeyboardButton(text=t["back_to_programs"], callback_data="back_programs")],
        ]
    )


# ---------------------------------------------------------------------------
# FSM HOLATLARI (ARIZA VA ADMIN E'LON)
# ---------------------------------------------------------------------------
class ApplicationStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_program = State()
    waiting_note = State()


class AdminBroadcastStates(StatesGroup):
    waiting_message = State()


# ---------------------------------------------------------------------------
# BOT ROUTER VA HANDLERLAR
# ---------------------------------------------------------------------------
router = Router()
bot_instance: Optional[Bot] = None


async def notify_admins_new_app(
    app_id: int, full_name: str, phone: str, program_code: str, program_title: str, note: str, source: str
) -> None:
    if not bot_instance or not ADMIN_IDS:
        return
    msg = (
        f"🔔 <b>YANGI ARIZA TUSHDI! (#{app_id})</b>\n\n"
        f"👤 <b>F.I.Sh:</b> {full_name}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"🎓 <b>Yo'nalish:</b> {program_code} — {program_title}\n"
        f"💬 <b>Izoh:</b> {note}\n"
        f"🌐 <b>Manba:</b> {source}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot_instance.send_message(admin_id, msg)
        except Exception as e:
            logger.warning(f"Adminga xabar yuborishda xatolik ({admin_id}): {e}")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_lang(user.id)
    t = TEXTS[lang]

    # Deep-link tekshirish: masalan /start apply_30610403
    args = (command.args or "").strip()
    if args.startswith("apply_"):
        code = args.replace("apply_", "").strip()
        if code in PROGRAMS:
            await state.update_data(preselected_code=code)
            await state.set_state(ApplicationStates.waiting_name)
            p_title = PROGRAMS[code]["title"][lang]
            await message.answer(
                f"🎯 <b>Tanlangan yo'nalish:</b> {code} — {p_title}\n\n{t['ask_name']}",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text=t["cancel_btn"])]],
                    resize_keyboard=True,
                ),
            )
            return

    await message.answer(
        t["welcome"],
        reply_markup=main_menu_kb(lang),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    user_id = message.from_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return
    st = get_stats()
    prog_lines = "\n".join(
        [f"  • <b>{code}</b>: {cnt} ta ariza" for code, cnt in st["by_program"].items()]
    ) or "  Hozircha arizalar yo'q"

    text = (
        "⚙️ <b>KARMANA 2-SON TEXNIKUMI — ADMIN PANEL</b>\n\n"
        f"👥 <b>Bot foydalanuvchilari:</b> {st['total_users']} ta\n"
        f"📝 <b>Jami kelib tushgan arizalar:</b> {st['total_applications']} ta\n\n"
        f"📊 <b>Yo'nalishlar kesimida:</b>\n{prog_lines}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Arizalarni CSV (Excel) yuklab olish", callback_data="admin_csv")],
            [InlineKeyboardButton(text="📢 Barchaga e'lon yuborish (Broadcast)", callback_data="admin_broadcast")],
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "admin_csv")
async def cb_admin_csv(call: CallbackQuery) -> None:
    if ADMIN_IDS and call.from_user.id not in ADMIN_IDS:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    csv_bytes = export_applications_csv()
    doc = BufferedInputFile(csv_bytes, filename="karmana_2_texnikum_arizalar.csv")
    await call.message.answer_document(
        doc,
        caption="📊 <b>Karmana tuman 2-son texnikumi — barcha kelib tushgan arizalar ro'yxati (CSV/Excel)</b>",
    )
    await call.answer()


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    if ADMIN_IDS and call.from_user.id not in ADMIN_IDS:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminBroadcastStates.waiting_message)
    await call.message.answer(
        "📢 Barcha foydalanuvchilarga yuboriladigan e'lon matnini yuboring (bekor qilish uchun /start bosing):"
    )
    await call.answer()


@router.message(AdminBroadcastStates.waiting_message)
async def process_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    with sqlite3.connect(DB_PATH) as conn:
        users = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
    sent = 0
    for uid in users:
        try:
            await message.copy_to(uid)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ E'lon {sent} ta foydalanuvchiga muvaffaqiyatli yuborildi!")


@router.callback_query(F.data.startswith("setlang_"))
async def cb_set_lang(call: CallbackQuery) -> None:
    lang = call.data.replace("setlang_", "")
    if lang not in TEXTS:
        lang = "uz"
    user = call.from_user
    upsert_user(user.id, user.username or "", user.full_name or "", lang=lang)
    t = TEXTS[lang]
    await call.message.delete()
    await call.message.answer(t["welcome"], reply_markup=main_menu_kb(lang))
    await call.answer()


# Asosiy menyu tugmalari
@router.message(F.text.in_({TEXTS["uz"]["menu_lang"], TEXTS["ru"]["menu_lang"], TEXTS["en"]["menu_lang"]}))
async def msg_change_lang(message: Message) -> None:
    await message.answer(
        "🌐 <b>Tilni tanlang / Выберите язык / Choose language:</b>",
        reply_markup=lang_inline_kb(),
    )


@router.message(F.text.in_({TEXTS["uz"]["menu_programs"], TEXTS["ru"]["menu_programs"], TEXTS["en"]["menu_programs"]}))
async def msg_programs(message: Message) -> None:
    lang = get_user_lang(message.from_user.id)
    await message.answer(
        TEXTS[lang]["choose_program"],
        reply_markup=programs_inline_kb(lang, prefix="prog_"),
    )


@router.callback_query(F.data == "back_programs")
async def cb_back_programs(call: CallbackQuery) -> None:
    lang = get_user_lang(call.from_user.id)
    await call.message.edit_text(
        TEXTS[lang]["choose_program"],
        reply_markup=programs_inline_kb(lang, prefix="prog_"),
    )
    await call.answer()


@router.callback_query(F.data.startswith("prog_"))
async def cb_program_detail(call: CallbackQuery) -> None:
    code = call.data.replace("prog_", "")
    lang = get_user_lang(call.from_user.id)
    p = PROGRAMS.get(code)
    if not p:
        await call.answer("Topilmadi")
        return
    quals_str = "\n".join([f"  • {q}" for q in p["quals"][lang]])
    text = (
        f"{p['icon']} <b>Kasb kodi: {p['code']}</b>\n"
        f"🎓 <b>Nomi:</b> {p['title'][lang]}\n"
        f"⏳ <b>O'qish muddati:</b> {p['duration']}\n"
        f"🤝 <b>Ta'lim shakli:</b> {p['form']}\n\n"
        f"🏅 <b>Beriladigan kvalifikatsiyalar:</b>\n{quals_str}"
    )
    await call.message.edit_text(text, reply_markup=program_detail_kb(code, lang))
    await call.answer()


@router.message(F.text.in_({TEXTS["uz"]["menu_dual"], TEXTS["ru"]["menu_dual"], TEXTS["en"]["menu_dual"]}))
async def msg_dual(message: Message) -> None:
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["dual_info"])


@router.message(F.text.in_({TEXTS["uz"]["menu_about"], TEXTS["ru"]["menu_about"], TEXTS["en"]["menu_about"]}))
async def msg_about(message: Message) -> None:
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["about_info"])


@router.message(F.text.in_({TEXTS["uz"]["menu_contact"], TEXTS["ru"]["menu_contact"], TEXTS["en"]["menu_contact"]}))
async def msg_contact(message: Message) -> None:
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["contact_info"].format(public_url=PUBLIC_URL))


# ---------------------------------------------------------------------------
# BOSQICHMA-BOSQICH ONLAYN ARIZA (FSM)
# ---------------------------------------------------------------------------
@router.message(F.text.in_({TEXTS["uz"]["cancel_btn"], TEXTS["ru"]["cancel_btn"], TEXTS["en"]["cancel_btn"]}))
async def msg_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["cancelled"], reply_markup=main_menu_kb(lang))


@router.message(F.text.in_({TEXTS["uz"]["menu_apply"], TEXTS["ru"]["menu_apply"], TEXTS["en"]["menu_apply"]}))
async def msg_start_apply(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    await state.set_state(ApplicationStates.waiting_name)
    await message.answer(
        t["ask_name"],
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=t["cancel_btn"])]],
            resize_keyboard=True,
        ),
    )


@router.callback_query(F.data.startswith("startapply_"))
async def cb_start_apply_program(call: CallbackQuery, state: FSMContext) -> None:
    code = call.data.replace("startapply_", "")
    lang = get_user_lang(call.from_user.id)
    t = TEXTS[lang]
    await state.clear()
    await state.update_data(preselected_code=code)
    await state.set_state(ApplicationStates.waiting_name)
    await call.message.answer(
        f"🎯 <b>{code} — {PROGRAMS[code]['title'][lang]}</b>\n\n{t['ask_name']}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=t["cancel_btn"])]],
            resize_keyboard=True,
        ),
    )
    await call.answer()


@router.message(ApplicationStates.waiting_name)
async def fsm_process_name(message: Message, state: FSMContext) -> None:
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    full_name = (message.text or "").strip()
    if len(full_name) < 3:
        await message.answer(t["ask_name"])
        return
    await state.update_data(full_name=full_name)
    await state.set_state(ApplicationStates.waiting_phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["share_phone_btn"], request_contact=True)],
            [KeyboardButton(text=t["cancel_btn"])],
        ],
        resize_keyboard=True,
    )
    await message.answer(t["ask_phone"], reply_markup=kb)


@router.message(ApplicationStates.waiting_phone)
async def fsm_process_phone(message: Message, state: FSMContext) -> None:
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()
    if len(phone) < 7:
        await message.answer(t["ask_phone"])
        return
    await state.update_data(phone=phone)
    data = await state.get_data()

    # Agar yo'nalish oldindan tanlangan bo'lsa, darhol izoh bosqichiga o'tamiz
    pre_code = data.get("preselected_code")
    if pre_code and pre_code in PROGRAMS:
        await state.update_data(program_code=pre_code)
        await state.set_state(ApplicationStates.waiting_note)
        await message.answer(
            t["ask_note"],
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=t["cancel_btn"])]],
                resize_keyboard=True,
            ),
        )
    else:
        await state.set_state(ApplicationStates.waiting_program)
        await message.answer(
            t["ask_program"],
            reply_markup=programs_inline_kb(lang, prefix="pickprog_"),
        )


@router.callback_query(ApplicationStates.waiting_program, F.data.startswith("pickprog_"))
async def fsm_pick_program(call: CallbackQuery, state: FSMContext) -> None:
    code = call.data.replace("pickprog_", "")
    lang = get_user_lang(call.from_user.id)
    t = TEXTS[lang]
    if code not in PROGRAMS:
        await call.answer("Xato tanlov")
        return
    await state.update_data(program_code=code)
    await state.set_state(ApplicationStates.waiting_note)
    await call.message.answer(
        f"✅ <b>{code} — {PROGRAMS[code]['title'][lang]}</b>\n\n{t['ask_note']}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=t["cancel_btn"])]],
            resize_keyboard=True,
        ),
    )
    await call.answer()


@router.message(ApplicationStates.waiting_note)
async def fsm_process_note(message: Message, state: FSMContext) -> None:
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    note = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()

    code = data.get("program_code", "30610403")
    p_title = PROGRAMS.get(code, PROGRAMS["30610403"])["title"][lang]
    full_name = data.get("full_name", message.from_user.full_name)
    phone = data.get("phone", "")

    app_id = save_application(
        user_id=message.from_user.id,
        full_name=full_name,
        phone=phone,
        program_code=code,
        program_title=p_title,
        note=note,
        source="telegram_bot",
    )

    await message.answer(
        t["app_success"].format(
            app_id=app_id,
            full_name=full_name,
            phone=phone,
            program=f"{code} — {p_title}",
            note=note,
        ),
        reply_markup=main_menu_kb(lang),
    )

    await notify_admins_new_app(
        app_id=app_id,
        full_name=full_name,
        phone=phone,
        program_code=code,
        program_title=p_title,
        note=note,
        source="Telegram Bot",
    )


# ---------------------------------------------------------------------------
# FASTAPI WEB SERVER (VEB-SAYT + REST API + TELEGRAM BOT LIFESPAN)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_instance
    init_db()
    polling_task = None
    if BOT_TOKEN:
        bot_instance = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        logger.info("Telegram Bot polling rejimida ishga tushmoqda...")
        polling_task = asyncio.create_task(dp.start_polling(bot_instance))
    else:
        logger.warning(
            "BOT_TOKEN topilmadi! Veb-sayt va API ishlayapti, Telegram botni ulash uchun BOT_TOKEN o'zgaruvchisini kiriting."
        )
    yield
    if polling_task:
        polling_task.cancel()
    if bot_instance:
        await bot_instance.session.close()


app = FastAPI(
    title="Karmana 2-son Texnikumi Web & Bot Server",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def serve_homepage():
    for candidate in ["index.html", "karmana_2_texnikum.html"]:
        p = BASE_DIR / candidate
        if p.exists():
            return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Karmana 2-son texnikumi serveri ishlamoqda!</h1>")


@app.post("/api/apply")
async def api_submit_application(request: Request):
    """Veb-saytdagi formadan kelgan arizalarni to'g'ridan-to'g'ri bazaga yozadi va Adminga Telegramdan yuboradi."""
    body = await request.json()
    full_name = str(body.get("full_name", "")).strip()
    phone = str(body.get("phone", "")).strip()
    program_raw = str(body.get("program", "30610403")).strip()
    note = str(body.get("note", "Veb-sayt orqali yuborildi")).strip()

    if not full_name or not phone:
        return JSONResponse({"ok": False, "error": "Ism va telefon raqami majburiy"}, status_code=400)

    code = program_raw[:8] if program_raw[:8] in PROGRAMS else "30610403"
    p_title = PROGRAMS[code]["title"]["uz"]

    app_id = save_application(
        user_id=0,
        full_name=full_name,
        phone=phone,
        program_code=code,
        program_title=p_title,
        note=note,
        source="website",
    )

    await notify_admins_new_app(
        app_id=app_id,
        full_name=full_name,
        phone=phone,
        program_code=code,
        program_title=p_title,
        note=note,
        source="Veb-sayt",
    )

    return JSONResponse({"ok": True, "application_id": app_id})


@app.get("/api/stats")
async def api_get_stats():
    return JSONResponse(get_stats())


if __name__ == "__main__":
    uvicorn.run("bot_and_server:app", host="0.0.0.0", port=PORT, reload=False)
