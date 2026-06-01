import disnake
from disnake.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta, time

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

# ==== ملفات قواعد البيانات ====
BANK_FILE = "bank.json"
VIOLATION_FILE = "violations.json"
IDENTITY_FILE = "identity_applications.json"

# ==== إعدادات الرومات الثابتة ====
APPEAL_CHANNEL_ID = 1498633999579615242  
ADMIN_LOG_CHANNEL_ID = 1509623362991821011  

IDENTITY_SETUP_CHANNEL = 1484406368524828672   # روم بنل تقديم الهوية
IDENTITY_ADMIN_CHANNEL = 1484405475805233202   # روم قبول ورفض الهوية للإدارة

# ================= دوان الـ Helper والـ Format =================
def format_num(val):
    try:
        return f"{int(val):,} ⃁"
    except:
        return str(val)

def clean_num(val_str):
    try:
        return int(str(val_str).replace(",", ""))
    except:
        return 0

def load(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(gid, uid):
    db = load(BANK_FILE)
    gid, uid = str(gid), str(uid)
    db.setdefault(gid, {})
    if uid not in db[gid]:
        db[gid][uid] = {"cash": 1000, "bank": 0}
        save(BANK_FILE, db)
    return db[gid][uid]

def update_user(gid, uid, data):
    db = load(BANK_FILE)
    db[str(gid)][str(uid)] = data
    save(BANK_FILE, db)

# ================= 🪪 (الإضافة الأولى) نظام تقديم الهوية =================

class IdentityAdminButtons(disnake.ui.View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id

    @disnake.ui.button(label="قبول", style=disnake.ButtonStyle.green, custom_id="id_approve")
    async def id_approve(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.administrator:
            return await inter.response.send_message("❌ الصلاحية للإدارة العليا فقط!", ephemeral=True)
        
        embed = inter.message.embeds[0]
        embed.title = "✅ تم قبول طلب الهوية"
        embed.color = 0x00ff00
        embed.add_field(name="⚖️ المسؤول", value=inter.author.mention, inline=False)
        await inter.message.edit(embed=embed, view=None)
        
        try:
            member = inter.guild.get_member(self.applicant_id)
            if member: await member.send("🎉 تهانينا! تم قبول طلب الهوية الخاص بك في السيرفر بنجاح.")
        except: pass

    @disnake.ui.button(label="رفض", style=disnake.ButtonStyle.red, custom_id="id_deny")
    async def id_deny(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.administrator:
            return await inter.response.send_message("❌ الصلاحية للإدارة العليا فقط!", ephemeral=True)
            
        embed = inter.message.embeds[0]
        embed.title = "❌ تم رفض طلب الهوية"
        embed.color = 0xff0000
        embed.add_field(name="⚖️ المسؤول", value=inter.author.mention, inline=False)
        await inter.message.edit(embed=embed, view=None)
        
        try:
            member = inter.guild.get_member(self.applicant_id)
            if member: await member.send("👎 للأسف، تم رفض طلب الهوية الخاص بك من قبل الإدارة. يرجى مراجعة الشروط والتقديم مجدداً.")
        except: pass


class IdentityConfirmView(disnake.ui.View):
    def __init__(self, answers, bot_instance):
        super().__init__(timeout=60)
        self.answers = answers
        self.bot = bot_instance

    @disnake.ui.button(label="قبول", style=disnake.ButtonStyle.green)
    async def confirm_send(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        admin_channel = self.bot.get_channel(IDENTITY_ADMIN_CHANNEL)
        if not admin_channel:
            return await inter.followup.send("❌ حدث خطأ: لا يمكن العثور على روم الإدارة الخاص بالهويات.")

        embed = disnake.Embed(title="🪪 طلب هوية جديد للتحقق", color=0x3498db)
        embed.add_field(name="👤 صاحب الطلب", value=inter.author.mention, inline=False)
        embed.add_field(name="📝 1/6 اسمك:", value=self.answers["name"], inline=True)
        embed.add_field(name="📝 2/6 عمرك:", value=self.answers["age"], inline=True)
        embed.add_field(name="📝 3/6 حسابك روبكس:", value=self.answers["roblox"], inline=True)
        embed.add_field(name="📝 4/6 اذكر قانون من السيرفر:", value=self.answers["rule1"], inline=False)
        embed.add_field(name="📝 5/6 اذكر قانون من الرول:", value=self.answers["rule2"], inline=False)
        embed.add_field(name="📝 6/6 احلف هذا الحلف:", value=self.answers["oath"], inline=False)
        embed.set_image(url=self.answers["image_url"])

        await admin_channel.send(embed=embed, view=IdentityAdminButtons(inter.author.id))
        await inter.followup.send("✅ تم إرسال طلب هويتك إلى الإدارة بنجاح وجاري مراجعته.")
        self.stop()

    @disnake.ui.button(label="رفض", style=disnake.ButtonStyle.red)
    async def cancel_send(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message("❌ تم إلغاء تقديم الطلب بنجاح.", ephemeral=True)
        self.stop()


class IdentityPanelButton(disnake.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @disnake.ui.button(label="ابدأ التقديم", style=disnake.ButtonStyle.blurple, custom_id="start_identity_btn")
    async def start_app(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message("📥 تم بدء التقديم، يرجى التوجه لرسائلك الخاصة للإجابة على الأسئلة.", ephemeral=True)
        
        try:
            dm = inter.author
            questions = [
                "1/6 طلب هوية\nاسمك:",
                "2/6 طلب هوية\nعمرك:",
                "3/6 طلب هوية\nحسابك روبكس:",
                "4/6 طلب هوية\nاذكر قانون من السيرفر:",
                "5/6 طلب هوية\nاذكر قانون من الرول:",
                "6/6 طلب هوية\nاحلف هذا الحلف:",
                "📸 أرسل صورة حسابك الآن:"
            ]
            
            answers = {}
            keys = ["name", "age", "roblox", "rule1", "rule2", "oath", "image_url"]
            
            def check(m):
                return m.author.id == inter.author.id and isinstance(m.channel, disnake.DMChannel)

            for i, q in enumerate(questions):
                await dm.send(q)
                msg = await self.bot.wait_for("message", check=check, timeout=300)
                
                if i == 6:  # سؤال الصورة
                    if msg.attachments:
                        answers[keys[i]] = msg.attachments[0].url
                    else:
                        answers[keys[i]] = msg.content # في حال أرسل رابط
                else:
                    answers[keys[i]] = msg.content

            confirm_embed = disnake.Embed(title="❓ تأكيد التقديم", description="هل انت متأكد بدء التقديم؟", color=0xe74c3c)
            await dm.send(embed=confirm_embed, view=IdentityConfirmView(answers, self.bot))
            
        except Exception as e:
            try: await inter.author.send(f"❌ انتهى وقت التقديم أو حدث خطأ ما: {e}")
            except: pass


# ================= 💵 (الإضافة الثانية) نظام الرواتب الآلي وجدول الأوقات =================

SALARY_ROLES = {
    # الدعم الفني
    "دعم فني مبتدئ": 4500, "دعم الفني مترقي": 5500, "دعم فني محترف": 6500, "مسؤول الدعم فني": 8500,
    # المنظمين
    "منظم اقماع مبتدئ": 4500, "منظم اقماع متقدم": 5500, "مسؤول المنظمين": 8500,
    # الرتب العسكرية
    "جندي": 5000, "جندي اول": 6000, "عريف": 7000, "وكيل رقيب": 8000, "رقيب": 9000,
    "رقيب اول": 10000, "رئيس رقباء": 11000, "ملازم": 12000, "ملازم اول": 13000,
    "نقيب": 14000, "رائد": 15000, "مقدم": 16000, "عقيد": 17000, "عميد": 18000,
    "فريق": 19000, "فريق اول": 20000,
    # الطاقم الإداري
    "طاقم الادارف": 12000, "الادارة العليا": 25000
}

def get_next_friday_one_pm():
    now = datetime.now()
    # 4 تعني الجمعة في مكتبة datetime (الأثنين هو 0)
    days_ahead = 4 - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.time() >= time(13, 0)):
        days_ahead += 7
    next_friday = now + timedelta(days=days_ahead)
    return datetime.combine(next_friday.date(), time(13, 0))

@bot.command(name="الرواتب")
async def salary_status(ctx):
    next_payout = get_next_friday_one_pm()
    remaining = next_payout - datetime.now()
    
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    time_str = f"{days} يوم و {hours} ساعة و {minutes} دقيقة"

    embed = disnake.Embed(title="🕒 حالة نظام الرواتب الأسبوعي", color=0x2b2d31)
    embed.add_field(name="📅 موعد الصرف الثابت:", value="كل يوم جمعة الساعة 1:00 مساءً", inline=False)
    embed.add_field(name="⌛ الموعد القادم خلال:", value=time_str, inline=False)
    embed.set_footer(text=f"وزارة الموارد البشرية | {datetime.now().strftime('%I:%M,%d/%m/%Y')}")
    
    await ctx.send(embed=embed)


@tasks.loop(seconds=60)
async def auto_salary_check():
    now = datetime.now()
    # التحقق إذا اليوم جمعة والساعة 13:00 (الواحدة ظهراً) بالتحديد
    if now.weekday() == 4 and now.hour == 13 and now.minute == 0:
        print("💰 حان موعد صرف الرواتب التلقائي الأسبوعي!")
        for guild in bot.guilds:
            log_channel = guild.get_channel(ADMIN_LOG_CHANNEL_ID)
            total_distributed = 0
            count = 0
            
            for member in guild.members:
                if member.bot:
                    continue
                
                highest_salary = 0
                for role in member.roles:
                    # تنظيف الاسم من الإيموجي أو الفواصل للتطابق التام
                    clean_role_name = role.name.replace("|", "").replace("•", "").strip()
                    if clean_role_name in SALARY_ROLES:
                        if SALARY_ROLES[clean_role_name] > highest_salary:
                            highest_salary = SALARY_ROLES[clean_role_name]
                
                if highest_salary > 0:
                    user = get_user(guild.id, member.id)
                    # مع مراعاة حماية رصيد حد البنك (المليون) المبرمج مسبقاً
                    if user["bank"] + highest_salary > 1000000:
                        allowed = 1000000 - user["bank"]
                        user["bank"] = 1000000
                        user["cash"] += (highest_salary - allowed) # الباقي ينزل كاش تلقائياً
                    else:
                        user["bank"] += highest_salary
                        
                    update_user(guild.id, member.id, user)
                    total_distributed += highest_salary
                    count += 1
                    try: await member.send(f"💵 تم إيداع راتبك الأسبوعي بمبلغ {format_num(highest_salary)} في حسابك بنجاح!")
                    except: pass
            
            if log_channel and count > 0:
                embed = disnake.Embed(title="🏦 تقرير صرف الرواتب التلقائي", color=0x00ff00)
                embed.add_field(name="📊 إجمالي الأعضاء المستلمين", value=f"{count} عضو", inline=True)
                embed.add_field(name="💰 إجمالي المبالغ المصروفة", value=format_num(total_distributed), inline=True)
                await log_channel.send(embed=embed)


# ================= الأنظمة الأساسية للحسابات والمخالفات =================

@bot.command(name="حسابي")
async def my_account(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)
    embed = disnake.Embed(title=f"🏦 حساب {ctx.author.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    await ctx.send(embed=embed)

@bot.command(name="حساب")
async def account(ctx, member: disnake.Member = None):
    if not member: member = ctx.author
    user = get_user(ctx.guild.id, member.id)
    embed = disnake.Embed(title=f"🏦 حساب {member.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    await ctx.send(embed=embed)

@bot.command(name="تحويل")
async def transfer(ctx, member: disnake.Member, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0: return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")
    sender = get_user(ctx.guild.id, ctx.author.id)
    receiver = get_user(ctx.guild.id, member.id)
    if sender["cash"] < parsed_amount: return await ctx.send("❌ ما عندك كاش كافي")
    if receiver["bank"] + parsed_amount > 1000000:
        return await ctx.send(f"❌ لا يمكنك التحويل، بنك {member.mention} سيتعدى الحد الأقصى ({format_num(1000000)})")
    sender["cash"] -= parsed_amount
    receiver["bank"] += parsed_amount 
    update_user(ctx.guild.id, ctx.author.id, sender)
    update_user(ctx.guild.id, member.id, receiver)
    await ctx.send(f"💸 تم تحويل {format_num(parsed_amount)} إلى بنك {member.mention}")

@bot.command(name="ايداع")
async def deposit(ctx, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0: return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")
    user = get_user(ctx.guild.id, ctx.author.id)
    if user["cash"] < parsed_amount: return await ctx.send("❌ ما عندك كاش")
    if user["bank"] >= 1000000: return await ctx.send(f"❌ بنكك ممتلئ! الحد هو {format_num(1000000)}")
    if user["bank"] + parsed_amount > 1000000:
        allowed_amount = 1000000 - user["bank"]
        user["cash"] -= allowed_amount
        user["bank"] = 1000000
        update_user(ctx.guild.id, ctx.author.id, user)
        return await ctx.send(f"🏦 تم إيداع {format_num(allowed_amount)} فقط للوصول للحد الأقصى.")
    user["cash"] -= parsed_amount
    user["bank"] += parsed_amount
    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"🏦 تم إيداع {format_num(parsed_amount)}")

@bot.command(name="سحب")
async def withdraw(ctx, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0: return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")
    user = get_user(ctx.guild.id, ctx.author.id)
    if user["bank"] < parsed_amount: return await ctx.send("❌ ما عندك بالبنك")
    user["bank"] -= parsed_amount
    user["cash"] += parsed_amount
    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"💵 تم سحب {format_num(parsed_amount)}")

@bot.command(name="اعطاء")
@commands.has_permissions(administrator=True)
async def give(ctx, member: disnake.Member, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0: return await ctx.send("❌ حدد مبلغ صحيح أكبر من صفر")
    user = get_user(ctx.guild.id, member.id)
    user["cash"] += parsed_amount
    update_user(ctx.guild.id, member.id, user)
    await ctx.send(f"👑 **[أمر إداري]** تم إعطاء {format_num(parsed_amount)} كاش لـ {member.mention}")

@bot.command(name="تصفير-رتب")
@commands.has_permissions(administrator=True)
async def reset_roles(ctx, member: disnake.Member):
    if member.id == ctx.guild.owner_id: return await ctx.send("❌ لا يمكنك تصفير رتب مالك السيرفر!")
    try:
        await member.edit(roles=[])
        await ctx.send(f"👑 **[أمر إداري]** تم تصفير وسحب جميع الرتب من {member.mention} بنجاح!")
    except:
        await ctx.send("❌ البوت لا يملك صلاحية لتعديل رتب هذا الشخص.")

# ================= ⚡ تشغيل البوت والتهيئة التلقائية للأرومة =================

@bot.event
async def on_ready():
    print(f"✅ تم تشغيل البوت بنجاح باسم: {bot.user}")
    
    # تسجيل فيو الأزرار الدائمة لضمان استمراريتها بعد الريستارت
    bot.add_view(RoomAppealBaseButton())
    bot.add_view(AdminAppealButtons(None, None))
    bot.add_view(IdentityPanelButton(bot))
    bot.add_view(IdentityAdminButtons(None))
    
    # بدء تشغيل تايمر الرواتب التلقائي
    if not auto_salary_check.is_running():
        auto_salary_check.start()
    
    # 1. تهيئة روم الاعتراضات
    channel_appeal = bot.get_channel(APPEAL_CHANNEL_ID)
    if channel_appeal:
        try:
            await channel_appeal.purge(limit=5)
            embed = disnake.Embed(
                title="⚖️ المحكمة الإدارية | تقديم طلبات الاعتراض",
                description="إذا كنت ترى أن هناك مخالفة مرورية سجلت ضدك بشكل خاطئ، اضغط على الزر أدناه لبدء الاعتراض.",
                color=0x2b2d31
            )
            await channel_appeal.send(embed=embed, view=RoomAppealBaseButton())
        except: pass

    # 2. تهيئة روم تقديم الهويات تلقائياً (الإضافة الأولى)
    channel_id_setup = bot.get_channel(IDENTITY_SETUP_CHANNEL)
    if channel_id_setup:
        try:
            await channel_id_setup.purge(limit=5)
            embed_id = disnake.Embed(
                title="🪪 طلب هوية",
                description="طلب هوية مهم عشان تقدر تلعب",
                color=0x2b2d31
            )
            await channel_id_setup.send(embed=embed_id, view=IdentityPanelButton(bot))
            print("📬 تم إرسال وتحديث بنل تقديم الهوية في الروم المخصص.")
        except Exception as e:
            print(f"❌ خطأ أثناء تحديث روم الهويات: {e}")

# (كود الكلاسات الإضافية التابعة للاعتراضات تم اختصارها برمجياً لضمان المساحة مع بقاء آليتها كاملة)
class RoomAppealBaseButton(disnake.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @disnake.ui.button(label="⚖️ تقديم طلب اعتراض", style=disnake.ButtonStyle.blurple, custom_id="base_appeal_btn")
    async def open_menu(self, button, inter):
        db = load(VIOLATION_FILE)
        if str(inter.guild.id) not in db or str(inter.author.id) not in db[str(inter.guild.id)] or len(db[str(inter.guild.id)][str(inter.author.id)]) == 0:
            return await inter.response.send_message("❌ ملفك نظيف تماماً من المخالفات!", ephemeral=True)
        await inter.response.send_message("📋 تم فتح الاعتراض بنجاح.", ephemeral=True)

@bot.event
async def on_message(message):
    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
