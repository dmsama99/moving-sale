# 迁到 Cloudflare Pages

这个分支（`cloudflare`）代码改动和 124 个 webp 都已经提交好了，**开箱可部署**。

迁移分两段，中间有个安全点：

```
第一段（在 Netlify 上做完）          第二段（切到 Cloudflare）
─────────────────────────          ─────────────────────────
push 到 Netlify 验证  ←── 安全点     建 Pages 项目
                                    临时域名自测
                                    删旧 DNS → 绑自定义域
                                    过一遍开关清单 → 验收
```

第一段做完，站还在 Netlify 上正常跑，只是不再依赖 Netlify 的图片接口了。
**这时候你已经可以随时停下来**——就算最后决定不迁 Cloudflare，这一段也是净赚。

---

## 这个分支改了什么

| 文件 | 改动 |
|---|---|
| `index.html` | 3 处，共 11 行。见下 |
| `build-images.sh` | **新增**。把 `photos/` 的原图预压成四档 webp |
| `photos/w96` `w400` `w800` `w1200` | **新增**，各 31 个 webp，共 124 个、4.45 MB |
| `README.md` | 更新了「加一件新东西」和「照片是怎么送到访客手上的」两节 |
| `netlify.toml` | **保留不动**。Cloudflare 直接忽略它，留着是为了随时能退回 Netlify |
| `photos/*.jpg` | **保留不动**。webp 万一出问题要靠原图兜底 |

`index.html` 的三处：

1. **`cdn()`（第 302 行）**——原来拼 `/.netlify/images?url=…&w=800&fm=webp`，
   现在拼 `photos/w800/i1.webp`。这是唯一一处 Netlify 专有依赖。
2. **`CDN_OK`（第 290 行）**——原来判断 `location.protocol !== "file:"`（本地双击打开时
   Netlify 接口不存在所以要关掉）。现在图是仓库里的静态文件，本地也能用，判断去掉了。
   **副作用是好的：以后本地双击 `index.html` 看到的效果和线上完全一致。**
3. **`CONFIG.USE_IMAGE_CDN` 的注释**——说明改了，开关本身没动。

**没改的东西**：第 601 行那段 `error` 兜底逻辑不用动，它用 `data-raw` 指向原始 jpg，
webp 缺档或加载失败照样退回原图。表格、`flavors.json`、快照、截图模式，全都没碰。

---

## 为什么图片这步不能跳

`index.html` 第 505 行，每张卡片的模糊背景层是 **`loading="eager"`**——31 张一进页面就全部开始下载。

预压后的 `photos/w96/` 实测 **33 KB / 31 张**（平均 1.1 KB）。
一旦这档缺失、走了第 601 行的兜底，这层会退回原图：

```
photos/*.jpg  实测 31 张（23 张 1200×900 + 8 张 900×1200）
              共 4,256,032 字节（4.06 MB），平均 134 KB/张
photos/w96/   实测 31 张，共 33,462 字节（33 KB），平均 1.1 KB/张
```

**首屏会从 33 KB 变成 4.06 MB，涨 127 倍，而且是并发的。** 国内手机网络下基本等于打不开。
所以「先搬上去再说，图片慢慢优化」这条路走不通——图片必须先解决，这个分支已经解决了。

---

## 第一段 · 在 Netlify 上做完（约 5 分钟）

### 1. 本地看一眼

直接双击 `index.html`。**现在本地预览是完整效果了**（改动 2 的好处），
图片该清楚清楚，不再是以前那种本地退回原图的样子。

### 2. push 到 Netlify 验证

```bash
git add -A
git commit -m "照片改为预压缩 webp，不再依赖平台图片接口"
git push -u origin cloudflare
```

Netlify 默认只自动部署主分支。要在线上验证有两个办法，**推荐第一个**：

- **合并进 `main` 再 push**——反正这一段改动本身就是净赚，不迁 Cloudflare 也该合。
- 或者在 Netlify 后台 Site configuration → Build & deploy → Branch deploys 里
  把 `cloudflare` 分支加进去，会给你一个 `cloudflare--站点名.netlify.app` 的预览地址。

线上打开，F12 → Network → 刷新，确认图片请求的是 `photos/w800/i1.webp` 这类路径、返回 200。
**看到 `/.netlify/images` 说明代码没生效；看到 `photos/i1.jpg`（不带 w800）说明 webp 没传上去。**

到这里第一段就完了。站还在 Netlify，一切正常，但已经不依赖它的图片接口了。

### 以后加新图怎么办

webp 已经压好提交进仓库了，平时不用管。只有**加了新照片或换了照片**才要重跑：

```bash
brew install webp        # 只有第一次需要（本机已装：webp 1.6.0）
./build-images.sh        # 已压过且原图没变的会自动跳过，很快
git add -A && git commit -m "加了 iN 的照片" && git push
```

实测产物（31 张原图 → 124 个 webp）：

```
w96     31 个     33 KB   平均 1.1 KB    模糊背景层，要糊 16px 所以压到 q45
w400    31 个    468 KB   平均 15.1 KB   手机窄屏
w800    31 个   1.33 MB   平均 44.1 KB   默认档，比原图省 67%
w1200   31 个   2.63 MB   平均 86.7 KB   大屏 / 高 DPI

webp 合计 4.45 MB + 原图 4.06 MB = 仓库图片 8.51 MB
```

GitHub 完全无压力（单文件上限 100 MB，仓库软上限 1 GB）。

> **关于 w1200 这档**：原图长边统一是 1200 px——31 张里 **23 张横的（1200×900）、8 张竖的（900×1200）**。
> 所以横图的 w1200 是货真价实的 1200 宽（比 w800 多 2.25 倍像素，这就是它占 2.63 MB 的原因），
> 竖图的 w1200 则是原尺寸 900 宽（脚本不放大）。这档留着值得，别删。
> 脚本会逐张比对原图宽度决定缩不缩，所以以后传任何尺寸的照片都不会被放大。

---

## 第二段 · 切到 Cloudflare

### 3. 建 Pages 项目

[dash.cloudflare.com](https://dash.cloudflare.com) → 左侧 **Workers & Pages**
→ **Create application** → **Pages** 标签 → **Connect to Git**
→ Sign in with GitHub → 授权 → 选 `dmsama99/moving-sale` → Install & Authorize
→ **Begin setup**

| 字段 | 填什么 |
|---|---|
| Project name | `moving-sale`（决定了临时域名 `moving-sale.pages.dev`） |
| Production branch | 你实际的主分支（`main`） |
| Framework preset | **None** |
| Build command | **留空** |
| Build output directory | **`.`** ← 一个英文句点 |
| Root directory | 留默认（空） |

> `.` 对应现在 `netlify.toml` 里的 `publish = "."`，前提是 `index.html` 在仓库**根目录**。
> 去 GitHub 仓库首页看一眼第一层有没有 `index.html`，别猜。

**Save and Deploy**，等一分钟。

### 4. 在临时域名上自测

打开 `https://moving-sale.pages.dev`。

> ⚠️ **别把这个地址发微信群或小红书。** `*.pages.dev` 在微信里被整域拦截，部分省份还有 DNS 污染。
> Cloudflare 官方 China Network FAQ 原文就写着 *"Pages is not available in Mainland China
> due to pages.dev certificate not residing within Mainland China"*。
> 这是预期现象，不是你部署失败。正式链接必须用自己的域名。

检查：
- [ ] 31 张图都出来了
- [ ] F12 → Network，图片是 `photos/w800/i1.webp`，200
- [ ] 顶部「库存已同步」正常（需要能连 Google，见文末「顺带一提」）

### 5. 切域名（零停机的关键在这里）

你的域名现在应该有一条指向 Netlify 的记录，橙云 proxied 状态。
**Cloudflare 不允许在已有 CNAME 的主机名上建自定义域名，所以必须先删再加。**

1. Cloudflare → 你的域名 → **DNS → Records**
2. 删掉指向 Netlify 的记录（CNAME 指向 `xxx.netlify.app`，或 A 指向 `75.2.60.5`）。
   `@` 和 `www` 都有就两条都删
3. **立刻**回到 **Workers & Pages → moving-sale → Custom domains → Set up a domain**
4. 填你的域名 → Continue → **Activate domain**
5. Cloudflare 会自动建一条指向 `moving-sale.pages.dev` 的 CNAME（橙云）。**别去手动改它**
6. `www` 要**单独再加一次**——Custom Domain 是精确主机名匹配，`example.com` 不会自动接管 `www.example.com`
7. 等状态变 **Active**

**为什么几乎没有停机**：记录一直是橙云代理，全世界解析到的始终是 Cloudflare 的 anycast IP，
Netlify 的地址只在 Cloudflare 内部当回源目标。所以**不用等 DNS 传播、不用等 TTL**。
真空窗口只有「旧记录已删、新域名还没 Active」这几十秒，期间访客看到的是 Cloudflare 错误页而不是解析失败。

> 你说的「证书好了」是 **Universal SSL**，**不等于**自定义域证书就绪。
> Pages 会为自定义域另签一张，一定要等状态变 Active 才算完成。

### 6. SSL/TLS 模式

**SSL/TLS → Overview**：

- 显示 **Automatic SSL/TLS**（新版默认）→ **保持不动**
- 老版 Custom 模式 → 选 **Full (Strict)**
- **绝对不要选 Flexible**——站点跑在 Pages 上时「源站」就是 Cloudflare 自己、只收 HTTPS，
  Flexible 等于让边缘用 HTTP 去请求一个只收 HTTPS 的源，结果是无限跳转直到 `ERR_TOO_MANY_REDIRECTS`

### 7. 顺手核一遍 DNS

Cloudflare 自动导入旧记录时不保证完整，重点看：

- **MX 记录**（这域名收邮件的话）。漏了或错了 → 邮件直接退信，而且你不会立刻发现
- **邮件服务器主机名的 A 记录**（比如 `mail.你的域名`）→ **必须是灰云**。
  点成橙云的话解析出的是 Cloudflare 的 HTTP 代理 IP，SMTP 25 端口不走 HTTP 代理，**收发信全断**
- **TXT 记录**（各类所有权验证、SPF）
- **CAA 记录**：有的话确认允许 Cloudflare 签证书，否则第 5 步的自定义域证书会失败。没有就不用管

---

## 必须检查的开关

Netlify 完全没有这类东西，**其中两个 Cloudflare 默认是开的**。

| | 设置 | 位置 | 设成 | 不处理会怎么坏 |
|---|---|---|---|---|
| 🔴 | **Bot Fight Mode** | Security → Bots | 关（默认关，确认） | 全域下发计算型质询，**免费版无法按路径豁免**（跑在 Ruleset Engine 之外，WAF Skip 和 Page Rules 都绕不过）。微信 iOS 内置浏览器有已知过不去 Cloudflare 质询的案例——验证框根本不显示，页面永远转圈。另外 `fetch("flavors.json")` 要是被质询，拿到的是 HTML 质询页而不是 JSON，`JSON.parse` 直接抛错，俏皮话全没 |
| 🔴 | **Browser Integrity Check** | Security → Settings | **关**（默认**开**） | 靠 UA 和 HTTP 头判断。微信 UA 带 `MicroMessenger`、小红书带 `xhs`，属非主流 UA，有误判可能。论坛里「没开 Under Attack 却出现 Checking your browser」多半是这个 |
| 🔴 | **Rocket Loader** | Speed → Optimization | 关（默认关，确认） | 它把所有 JS 延到渲染后异步执行。`index.html` 是 48 KB 内联 JS，依赖 `DOMContentLoaded` 的初始化会在事件早就触发完之后才跑 → **初始化永不执行，白屏** |
| 🔴 | **Security Level** | Security → Settings | 保持 Medium。**别调 High，别开 Under Attack** | 国内住宅 IP（尤其移动/联通 NAT 大出口）威胁分偶尔偏高，调 High 明显增加误弹质询 |
| 🟡 | **Email Address Obfuscation** | Security → Settings | **关**（默认**开**） | 把邮箱样式文本改写成 `/cdn-cgi/l/email-protection#…` 并注入解码 JS。现在页面里没有邮箱所以没事，但以后写了联系邮箱、或内联 JS 字符串里出现 `x@y.z`，HTML 会被就地改写，脚本可能崩 |
| 🟡 | **别建任何 Cache Rule** | Caching → Cache Rules | 一条都别建 | 默认只按扩展名缓存静态资源，HTML 和 JSON **默认不缓存**，所以 push 完立刻生效。一旦为了「加速」建条 Cache Everything，`index.html` 就被缓存住，之后每次改内容都要手动 Purge。**遇到「改了不更新」，去 Caching → Configuration → Purge Everything，别去建规则** |

一句话：**Security 那栏全部关闭/默认，Speed 和 Caching 一个都别动。**
你需要 Cloudflare 做的只有两件事——托管静态文件、给不限量带宽。

---

## 验收

用**你自己的域名**（不是 pages.dev）打开：

- [ ] `https://你的域名` 能开，地址栏有锁
- [ ] 故意敲 `http://你的域名`，自动跳 https，**不是**无限跳转报错
- [ ] `www.你的域名` 也能开
- [ ] 31 件东西照片都在，比以前清楚
- [ ] F12 → Network，图片是 `photos/w800/i1.webp`，200，单张 40–55 KB 量级
- [ ] 顶部显示「库存已同步 · HH:MM」
- [ ] 卡片小字显示「2022 年入手」这类年份
- [ ] 表格里勾一件 `sold` → 等 5 分钟 → 页面点「刷新」→ 盖上「已出」章
- [ ] 点「截图模式」，等提示「图片都齐了」再截
- [ ] **手机上用微信打开你的域名**（发给自己），确认不弹验证页、不转圈
- [ ] 改一行 `flavors.json` → push → 一分钟后刷新页面，文案变了（确认没有缓存规则挡住）

---

## 出问题怎么办

**图全是「暂无实拍」**
`photos/w800/` 之类没传上去。GitHub 仓库里点进去看一眼四个目录在不在、里面有没有 31 个文件。

**图显示了但很糊 / 很大**
F12 看请求的是不是 `photos/i1.jpg`（不带 `w800`）。是的话说明 webp 缺档走了兜底，重跑 `./build-images.sh --force` 再 push。

**页面白屏 / 卡片不渲染**
八成是 Rocket Loader 被开了。Speed → Optimization 里关掉，然后 Purge Everything。

**访客说打不开 / 一直转圈**
Bot Fight Mode 或 Browser Integrity Check。上面清单里那两项关掉。

**改了代码线上不变**
Caching → Configuration → **Purge Everything**。然后检查是不是建了 Cache Rule。

**邮件收不到了**
DNS 里 MX 记录漏了，或者邮件服务器主机名的 A 记录被点成了橙云。

### 怎么退回 Netlify

`netlify.toml` 和 `photos/*.jpg` 都留着没删，所以退回很干净：

1. Cloudflare → Workers & Pages → moving-sale → Custom domains → 删掉自定义域
2. DNS → Records → 加回指向 Netlify 的那条 CNAME（橙云或灰云都行）
3. 代码**不用回滚**——预压缩的 webp 在 Netlify 上一样是普通静态文件，照样正常

---

## 费用

**每月 $0.00**，而且不存在意外账单的技术路径：免费计划的资源要么不计量（带宽、静态请求），
要么是硬上限（超了报错，不扣钱）。不绑付款方式就不可能出账单。

| | 免费额度 | 你的用量 |
|---|---|---|
| Pages 构建 | 500 次/月 | 每月几十次 push |
| 文件数 | 20,000 个 | 约 157 个（0.8%） |
| 单文件 | 25 MiB | 最大不到 300 KB |
| **带宽** | **不计量，无上限** | — |
| **静态资源请求** | 官方原文 *"free and unlimited"* | — |

**别买这些**（控制台里和免费功能混排，容易误点）：

| 加购项 | 价格 | 为什么不买 |
|---|---|---|
| Argo Smart Routing | $5/域名/月 **+ $0.10/GB，无上限** | 优化的是回源那一跳。纯静态站全命中边缘缓存、根本不回源，收益为零 |
| Pro 计划 | $25/月 | 你需要的功能免费版全有。Polish（自动压图）要 Pro，但它只压缩不改尺寸，撑不起 srcset，对你没用 |
| Advanced Certificate Manager | $10/月 | Universal SSL 已覆盖主域 + 一级泛域名 |
| Load Balancing | $5/月起 | 你没有多个源站 |
| Client-Side Security 高级版 | $0.099/千请求，**无上限** | 页面没引任何第三方 JS |

想加访问统计的话用 **Cloudflare Web Analytics**——免费、无额度限制、无 Cookie。别用 Zaraz。

---

## 可选：改用 Cloudflare 的 `/cdn-cgi/image/`

**不推荐，但记在这里以防以后嫌跑脚本麻烦。** 好处是加新图不用再跑 `build-images.sh`。

把 `cdn()` 改成：

```js
function cdn(src, w){
  if(!CDN_OK || isAbs(src)) return src;
  return "/cdn-cgi/image/format=auto,width=" + w + ",quality=82,fit=scale-down,onerror=redirect/" + src;
}
```

注意是**路径式**语法（选项和图片路径之间是斜杠，不是问号），**不要** `encodeURIComponent`。
`format=auto` 比写死 webp 还好：支持 AVIF 的浏览器拿 AVIF（再小 20–30%），Safari 拿 webp，
而按官方计费口径多种格式只算一次转换。`onerror=redirect` 在转换失败时自动 302 到原图。

三个前置条件，最容易卡在这里：

1. 域名必须橙云 proxied（绑了自定义域自动满足）
2. **后台要手动开**：Images → Transformations → 选中域名 → **Enable transformations**。默认是关的
3. **`*.pages.dev` 上用不了**（官方错误码 9524 明确写 *"use a Custom Domain"*）
   → 所以第 4 步用临时域名自测时图片一定失败，**这是预期现象**，必须绑完自定义域才能测

费用也是 $0：免费额度 5,000 次 unique transformations/月，
你 31 图 × 4 档 = **124 次/月，占 2.5%**。超额只报错（9422）不扣钱。

**代价**：重新把图片绑死在平台上——换回 Netlify、换到 GitHub Pages、本地双击打开，全都失效。
预压缩方案没有这个问题。所以除非你真的嫌跑脚本烦，否则不值得。

> 顺便澄清两个网上常见的过时说法：
> **Polish** 免费版没有，要 $25/月的 Pro，而且只压缩不改尺寸。
> **Mirage**（会重写 `<img>` 和自己的 srcset 打架）**已经在 2025-09-15 下线了**，没什么可关的。

---

## 顺带一提：两个跟迁移无关但更严重的问题

**1. 大陆访客拿不到实时库存。**
`index.html` 第 202 行 `SHEET_CSV_URL` 指向 `docs.google.com`，Google 全线域名在大陆被封。
访客几乎全从微信和小红书来，他们看到的永远是 `BAKED` 那份内置快照，顶部还会显示「没连上表格」。
代码用了 `cache:"no-store"` 且每次切回标签页都重拉，等于每次都白卡一轮超时。
**这个问题换到 Cloudflare、Vercel、GitHub Pages 都一样存在，跟迁不迁没关系。**

治本要么把库存改成 push 时烘进 HTML（放弃实时性，换来大陆可用），
要么把 CSV 代理一层（自己写个 Cloudflare Worker 转发，但 Worker 出网同样要能连 Google，
在 Cloudflare 边缘上是能连的——这条路可行，只是要多写点东西）。

**2. `CONFIG.SHOW_OFFLINE_HINT: true`** 让上面那件事直接暴露给访客。
在治本之前，至少可以先改成 `false` 静默用快照。

这两条这个分支都没动——是产品取舍，得你定。
