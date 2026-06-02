import discord
from discord.ext import commands, tasks
import os
import json
from datetime import datetime

# 1. إعدادات البوت الأساسية
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# نص الحلف الافتراضي
OATH_TEXT_ORIGINAL = "أقسم بالله العظيم أن التزم بقوانين السيرفر وأن أحترم الجميع"

# روم الإدارة (⚠️ استبدل هذا الرقم بـ ID روم الإدارة الفعلي في سيرفرك)
ADMIN_CHANNEL_ID = 123456789012345678 

# 2. إعدادات نظام الرواتب بناءً على صور سيرفرك
SALARY_CONFIG = {
    "دعم فني مبتدئ": 4500,
    "دعم الفني مترفي": 5550,
    "دعم فني محترف": 6500,
    "مسؤول الدعم فني": 8500,
    "منظم اقناع مبتدئ": 4500,
    "منظم اقناع متقدم": 5500,
    "منظم اقناع خبير": 7500,
    "مسؤول المنظمين": 8500,
    "جندي": 5000,
    "جندي اول": 6000,
    "عريف": 7000,
    "وكيل رقيب": 8000,
    "رقيب": 9000,
    "رقيب اول": 10000,
    "رئيس رقباء": 11000,
    "ملازم": 12000,
    "ملازم اول": 13000,
    "نقيب": 14000,
    "رائد": 15000,
    "مقدم": 16000,
    "عقيد": 17000,
    "عميد": 18000,
    "فريق": 19000,
    "فريق اول": 20000,
    "طاقم الاداره": 12000,
    "الاداره العليا": 25000
}

# ملف حفظ بيانات البنك (قاعدة بيانات مصغرة)
BANK_FILE = "bank_data.json"

def load_bank():
    if os.path.exists(BANK_FILE):
        with open(BANK_FILE, "r") as f:
            return json.load(f)
    return {}

def save_bank(data):
    with open(BANK_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 3. واجهة نظام أزرار القبول والرفض للتقديمات
class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="قبول", style=discord.ButtonStyle.green, custom_id="approve_btn")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        admin_roles = ["طاقم الاداره", "الاداره العليا"]
        has_permission = any(role.name in admin_roles for role in interaction.user.roles)
        
        if not has_permission:
            await interaction.response.send_message("❌ عذراً، هذا الزر مخصص لطاقم الإدارة فقط!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ تم قبول طلب التقديم"
        embed.set_footer(text="تم القبول بواسطة: " + str(interaction.user.name))
        
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send("✅ تم قبول العضو بنجاح.", ephemeral=True)

    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red, custom_id="deny_btn")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        admin_roles = ["طاقم الاداره", "الاداره العليا"]
        has_permission = any(role.name in admin_roles for role in interaction.user.roles)
        
        if not has_permission:
            await interaction.response.send_message("❌ عذراً، هذا الزر مخصص لطاقم الإدارة فقط!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ تم رفض طلب التقديم"
        embed.set_footer(text="تم الرفض بواسطة: " + str(interaction.user.name))
        
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send("❌ تم رفض الطلب.", ephemeral=True)

# واجهة زر "ابدأ التقديم" للمستخدمين
class StartFormView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ابدأ التقديم", style=discord.ButtonStyle.blurple, custom_id="start_apply_btn")
    async def start_apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.guild.get_channel(ADMIN_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="📝 طلب تقديم جديد", color=discord.Color.orange())
            embed.add_field(name="المقدم:", value=interaction.user.mention, inline=True)
            
            # الصياغة العادية والآمنة 100% لمنع خطأ الـ Crashed
            oath_text = "```\n(" + str(OATH_TEXT_ORIGINAL) + ")\n```"
            embed.add_field(name="📜 الـحـلـف المـطـلـوب (الأصـلـي):", value=oath_text, inline=False)
            
            await channel.send(embed=embed, view=ApplicationView())
            await interaction.response.send_message("✅ تم إرسال طلبك إلى طاقم الإدارة بنجاح!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ خطأ: لم يتم العثور على روم الإدارة المطلوبة.", ephemeral=True)

# 4. نظام الرواتب التلقائي والبنك
@tasks.loop(hours=168) # 168 ساعة تعني مرة كل أسبوع (كل يوم جمعة مثلاً)
async def weekly_salary_distributor():
    # كود لتوزيع الرواتب تلقائياً بناءً على الرتبة
    bank = load_bank()
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            
            highest_salary = 0
            for role in member.roles:
                if role.name in SALARY_CONFIG:
                    if SALARY_CONFIG[role.name] > highest_salary:
                        highest_salary = SALARY_CONFIG[role.name]
            
            if highest_salary > 0:
                user_id = str(member.id)
                if user_id not in bank:
                    bank[user_id] = {"balance": 0, "salary": highest_salary}
                
                bank[user_id]["balance"] += highest_salary
                bank[user_id]["salary"] = highest_salary
    save_bank(bank)
    print("💰 [النظام] تم توزيع الرواتب الأسبوعية بنجاح لجميع الموظفين والأعضاء المستحقين.")

# 5. أوامر البنك (الرصيد، توزيع يدوي، تحويل)
@bot.command(name="رصيدي", aliases=["فلوسي", "البنك"])
async def check_balance(ctx):
    bank = load_bank()
    user_id = str(ctx.author.id)
    balance = bank.get(user_id, {}).get("balance", 0)
    
    embed = discord.Embed(title="🏦 بنك سيرفر BlackNight", color=discord.Color.gold())
    embed.add_field(name="الحساب الخاص بك:", value=ctx.author.mention, inline=False)
    embed.add_field(name="💰 الرصيد الحالي:", value=f"**{balance:,}** ريال/نقطة", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="صرف_رواتب")
@commands.has_permissions(administrator=True)
async def force_salary(ctx):
    # أمر إداري لصرف الرواتب يدوياً فوراً في أي وقت
    bank = load_bank()
    count = 0
    for member in ctx.guild.members:
        if member.bot:
            continue
        highest_salary = 0
        for role in member.roles:
            if role.name in SALARY_CONFIG:
                if SALARY_CONFIG[role.name] > highest_salary:
                    highest_salary = SALARY_CONFIG[role.name]
        
        if highest_salary > 0:
            user_id = str(member.id)
            if user_id not in bank:
                bank[user_id] = {"balance": 0, "salary": highest_salary}
            bank[user_id]["balance"] += highest_salary
            bank[user_id]["salary"] = highest_salary
            count += 1
            
    save_bank(bank)
    await ctx.send(f"✅ تم توزيع الرواتب يدوياً بنجاح لـ **{count}** عضو/موظف مسجل حسب رتبته.")

# 6. أحداث تشغيل البوت (Events)
@bot.event
async def on_ready():
    bot.add_view(StartFormView())
    bot.add_view(ApplicationView())
    if not weekly_salary_distributor.is_running():
        weekly_salary_distributor.start()
    print(f"✅ تم تشغيل البوت بنجاح باسم: {bot.user}")

# 7. أوامر إنشاء غرف التقديم والبنك
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_apply(ctx):
    embed = discord.Embed(
        title="🎮 تصريح سيرفر",
        description="تصrichten سيرفر مهم عشان تقدر تلعب معنا وتدخل السيرفر الرسمي.",
        color=discord.Color.dark_theme()
    )
    await ctx.send(embed=embed, view=StartFormView())
    await ctx.message.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_bank_info(ctx):
    embed = discord.Embed(
        title="🕒 حالة نظام الرواتب الأسبوعي",
        description="**موعد الصرف الثابت:**\nكل يوم جمعة الساعة 1:00 مساءً\n\n**الموعد القادم خلال:**\nيتم التحديث والصرف تلقائياً عبر النظام البنكي التابع للإدارة.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="وزارة الموارد البشرية | BlackNight")
    await ctx.send(embed=embed)
    await ctx.message.delete()

# تشغيل البوت
TOKEN = os.getenv("DISCORD_TOKEN", "ضع_توكن_البوت_هنا")
bot.run(TOKEN)
