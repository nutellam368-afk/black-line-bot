import disnake
from disnake.ext import commands
import json, os

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

BANK_FILE = "bank.json"
VIOLATION_FILE = "violations.json"

# دالة مسابقة لتنسيق الأرقام بالفواصل مع رمز العملة ⃁
def format_num(val):
    try:
        return f"{int(val):,} ⃁"
    except:
        return f"{str(val)} ⃁"

# دالة لتنظيف الرقم المدخل من الفواصل
def clean_num(val_str):
    try:
        return int(str(val_str).replace(",", ""))
    except:
        return 0

# ================= DATABASE =================
def load(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ================= USER =================
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

# ================= حساب =================
@bot.command(name="حسابي")
async def my_account(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)

    embed = disnake.Embed(title=f"🏦 حساب {ctx.author.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command(name="حساب")
async def account(ctx, member: disnake.Member = None):
    if not member:
        member = ctx.author

    user = get_user(ctx.guild.id, member.id)

    embed = disnake.Embed(title=f"🏦 حساب {member.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# ================= تحويل =================
@bot.command(name="تحويل")
async def transfer(ctx, member: disnake.Member, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")

    sender = get_user(ctx.guild.id, ctx.author.id)
    receiver = get_user(ctx.guild.id, member.id)

    if sender["cash"] < parsed_amount:
        return await ctx.send("❌ ما عندك كاش كافي")

    if receiver["bank"] + parsed_amount > 1000000:
        return await ctx.send(f"❌ لا يمكنك التحويل، بنك {member.mention} سيتعدى الحد الأقصى ({format_num(1000000)})")

    sender["cash"] -= parsed_amount
    receiver["bank"] += parsed_amount 

    update_user(ctx.guild.id, ctx.author.id, sender)
    update_user(ctx.guild.id, member.id, receiver)

    await ctx.send(f"💸 تم تحويل {format_num(parsed_amount)} إلى بنك {member.mention}")

# ================= ايداع / سحب =================
@bot.command(name="ايداع")
async def deposit(ctx, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")

    user = get_user(ctx.guild.id, ctx.author.id)

    if user["cash"] < parsed_amount:
        return await ctx.send("❌ ما عندك كاش")

    if user["bank"] >= 1000000:
        return await ctx.send(f"❌ بنكك ممتلئ بالفعل! الحد الأقصى هو {format_num(1000000)}")

    if user["bank"] + parsed_amount > 1000000:
        allowed_amount = 1000000 - user["bank"]
        user["cash"] -= allowed_amount
        user["bank"] = 1000000
        update_user(ctx.guild.id, ctx.author.id, user)
        return await ctx.send(f"🏦 تم إيداع {format_num(allowed_amount)} فقط لأن البنك وصل للحد الأقصى ({format_num(1000000)})")

    user["cash"] -= parsed_amount
    user["bank"] += parsed_amount

    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"🏦 تم إيداع {format_num(parsed_amount)}")

@bot.command(name="سحب")
async def withdraw(ctx, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")

    user = get_user(ctx.guild.id, ctx.author.id)

    if user["bank"] < parsed_amount:
        return await ctx.send("❌ ما عندك بالبنك")

    user["bank"] -= parsed_amount
    user["cash"] += parsed_amount

    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"💵 تم سحب {format_num(parsed_amount)}")

# ================= 👑 أوامر الإدارة العليا فقط (ليست للعساكر) =================

@bot.command(name="اعطاء")
@commands.has_permissions(administrator=True) # للإدارة فقط
async def give(ctx, member: disnake.Member, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ الرجاء تحديد مبلغ صحيح أكبر من صفر")

    user = get_user(ctx.guild.id, member.id)
    user["cash"] += parsed_amount
    update_user(ctx.guild.id, member.id, user)

    await ctx.send(f"👑 **[أمر إداري]** تم إعطاء {format_num(parsed_amount)} كاش لـ {member.mention}")

@bot.command(name="حساب-السيرفر")
@commands.has_permissions(administrator=True) # للإدارة فقط
async def server_accounts(ctx):
    db = load(BANK_FILE)
    gid = str(ctx.guild.id)

    if gid not in db or not db[gid]:
        return await ctx.send("❌ لا يوجد بيانات أعضاء في هذا السيرفر")

    embed = disnake.Embed(title="📊 حسابات السيرفر (إدارة عليا)", color=0x2b2d31)

    for uid, data in db[gid].items():
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"عضو غادر ({uid})"

        embed.add_field(
            name=f"👤 {name}",
            value=f"💵 كاش: {format_num(data['cash'])} | 🏦 بنك: {format_num(data['bank'])}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name="الغاء-مخالفة")
@commands.has_permissions(administrator=True) # للإدارة فقط ومستحيل عسكري يسويها
async def clear_violations(ctx, member: disnake.Member):
    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)
    uid = str(member.id)

    if gid not in db or uid not in db[gid] or len(db[gid][uid]) == 0:
        return await ctx.send(f"❌ {member.mention} ليس لديه أي مخالفات مسجلة ليتم إلغاؤها")

    db[gid].pop(uid)
    save(VIOLATION_FILE, db)

    await ctx.send(f"✅ **[أمر إداري]** تم إلغاء وتصفير جميع مخالفات {member.mention} بنجاح!")

# ================= 🚓 نظام المخالفات (متاح للعساكر/الجميع) =================
VIOLATIONS = [
    ("زره", "500"),
    ("قطع اشاره", "3000"),
    ("سحب جلنط", "1000"),
]

class ViolationSelect(disnake.ui.Select):
    def __init__(self, member, officer, image):
        options = [disnake.SelectOption(label=f"{v[0]} | {format_num(v[1])}") for v in VIOLATIONS]
        super().__init__(placeholder="اختر المخالفة", options=options)

        self.member = member
        self.officer = officer
        self.image = image

    async def callback(self, inter):
        selected = self.values[0].split(" | ")[0]
        fine = next(v[1] for v in VIOLATIONS if v[0] == selected)

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(self.member.id)

        db.setdefault(gid, {}).setdefault(uid, [])
        db[gid][uid].append({
            "type": selected,
            "fine": fine,
            "officer": str(self.officer),
            "image": self.image
        })
        save(VIOLATION_FILE, db)

        embed = disnake.Embed(title="🚨 تم تسجيل مخالفة", color=0xff0000)
        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="👮 العسكري", value=self.officer.mention)
        embed.add_field(name="📄 المخالفة", value=selected)
        embed.add_field(name="💰 الغرامة", value=format_num(fine))

        if self.image:
            embed.set_image(url=self.image)

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class ViolationView(disnake.ui.View):
    def __init__(self, member, officer, image):
        super().__init__()
        self.add_item(ViolationSelect(member, officer, image))

@bot.command(name="مخالفة")
async def violation(ctx, member: disnake.Member):
    image = None
    if ctx.message.attachments:
        image = ctx.message.attachments[0].url

    embed = disnake.Embed(title="🚓 نظام المخالفات", color=0x2b2d31)
    if image:
        embed.set_image(url=image)

    await ctx.send(embed=embed, view=ViolationView(member, ctx.author, image))

# ================= تسديد =================
class PaySelect(disnake.ui.Select):
    def __init__(self, violations):
        options = [disnake.SelectOption(label=f"{v['type']} | {format_num(v['fine'])}") for v in violations]
        super().__init__(placeholder="اختر للدفع", options=options)
        self.violations = violations

    async def callback(self, inter):
        selected = self.values[0].split(" | ")[0]

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(inter.author.id)

        chosen = None
        for v in self.violations:
            if v["type"] == selected:
                chosen = v
                break

        if not chosen or not str(chosen["fine"]).isdigit():
            return await inter.response.send_message("❌ ما تقدر تدفعها", ephemeral=True)

        user = get_user(inter.guild.id, inter.author.id)

        if user["bank"] < int(chosen["fine"]):
            return await inter.response.send_message("❌ البنك ما يكفي", ephemeral=True)

        user["bank"] -= int(chosen["fine"])
        update_user(inter.guild.id, inter.author.id, user)

        db[gid][uid].remove(chosen)
        save(VIOLATION_FILE, db)

        embed = disnake.Embed(title="✅ تم التسديد", color=0x00ff00)
        embed.add_field(name="👤 المواطن", value=inter.author.mention)
        embed.add_field(name="👮 العسكري", value=chosen["officer"])
        embed.add_field(name="📄 المخالفة", value=chosen["type"])
        embed.add_field(name="💰 الغرامة", value=format_num(chosen["fine"]))

        if chosen["image"]:
            embed.set_image(url=chosen["image"])

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class PayView(disnake.ui.View):
    def __init__(self, violations):
        super().__init__()
        self.add_item(PaySelect(violations))

@bot.command(name="تسديد")
async def pay(ctx):
    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if gid not in db or uid not in db[gid] or len(db[gid][uid]) == 0:
        return await ctx.send("❌ ما عندك مخالفات")

    embed = disnake.Embed(title="💳 اختر مخالفة للتسديد", color=0x2b2d31)
    await ctx.send(embed=embed, view=PayView(db[gid][uid]))

# =================
@bot.event
async def on_message(message):
    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
