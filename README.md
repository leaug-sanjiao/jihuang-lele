# 荒野合成手册

《饥困荒野》手游的本地查询工具。可以查物品配方、从材料反查用途、记录背包后筛选能做的物品，以及展开中间材料和最终缺项。使用 Vue 3、TypeScript 和 Vite，页面适配手机及桌面。

## Windows 本地使用

需要 Node.js **22.12 或更高的 22.x**，也可用 Node.js 24 及后续版本。解压后，在包含 package.json 的文件夹打开 PowerShell。

~~~powershell
npm.cmd install
npm.cmd run dev
~~~

在浏览器打开 [http://localhost:5173](http://localhost:5173)。首次安装依赖需要联网。页面从本地数据文件读取配方，只有主动打开来源链接才会访问 Wiki。数量和科技勾选保存在当前浏览器，和设备、浏览器及访问地址绑定。

## 查询和合成规划

- **合成配方**从页首按成品或材料搜索，切换分类时保留关键词。点击材料名称可反查用途，在详情的「背包 / 需求」一栏直接填写库存。
- **材料反查**按材料关键字查找直接使用它的配方。点选匹配的材料名可精确筛选，支持分别查看合成和料理。例如反查「树枝」会返回斧头等装备和使用树枝的料理示例。
- **用途筛选**可与材料反查、背包状态一起使用。选择「工具」可查看斧头、鹤嘴锄、铲子等。搜索支持「斧子」「镐子」等常用叫法。「铁镐」可搜到相关采矿工具，该名称仍待实机确认。
- **可制造筛选**按每条配方做一次的直接材料分开判断。「只看材料齐全」也会保留科技待查的配方。「材料与科技齐全」只保留有明确科技记录且满足条件的合成配方。已解锁的科技在背包中手动勾选。
- **递归合成树**按详情中的制作次数计算。一棵树共享同一份材料库存，优先分配现有材料。对录有确定用量与产量的中间配方，会展开制作次数和材料；未收录的配方、未明确的用量或产量会停在对应节点。预估结果只用来备料，打开合成树不会扣除背包。
- **料理查询**显示 Wiki 的投料示例、需求、限制和已记录的属性。「食材齐」表示手头食材满足该示例，实际成品、烹饪设备和食材替代规则仍需以游戏为准。
- 例如在「炼金引擎」详情里，合成树会从木板、石砖和电子元件继续展开到木头、石头和金块。

## 数据来源与参数边界

截至 **2026-11-25**，收录 **189 条有材料用量的制造配方、7 条制造参考记录、71 种料理和 2 条火烤做法**。其中 141 条来自本次扩充的社区图鉴，可按护甲、航海、工具、生存等用途查找。料理有 77 条记录，同一道菜的不同投料方式分别参与材料反查和背包计算。

点击配方里的材料、在背包中选「查用途与来源」，或直接搜索材料全名，可查看获取方式、特殊用途及使用它的制造和料理。材料资料来自道具和食物图鉴的 216 条历史记录，并关联已收录配方和 127 个生物的资料。例如树枝可从树苗采集，犬牙能查到猎犬等来源，木板能打开自身制作记录。生物关联不保证击杀必掉，概率、数量和特殊条件以游戏内为准。

| 来源 | 页面更新时间 / 修订 | 取用范围 |
| --- | --- | --- |
| [制造图鉴](https://wiki.biligame.com/jikunhuangye/制造图鉴) | 2024-03-22 / 2602 | 营火一条 |
| [装备图鉴](https://wiki.biligame.com/jikunhuangye/装备图鉴) | 2024-03-22 / 2600 | 斧头、木甲、火腿棒、步行手杖 |
| [食物图鉴](https://wiki.biligame.com/jikunhuangye/食物图鉴) | 2024-03-22 / 2599 | 表中 207 行，71 行被标为料理 |
| [道具图鉴](https://wiki.biligame.com/jikunhuangye/道具图鉴) | 2024-03-22 / 2601 | 表中 164 行，识别出木板、绳子等缺少用量的合成产物 |
| [家园速生指南](https://wiki.biligame.com/jikunhuangye/【饥困荒野】家园速生指南) | 2024-03-18 / 1718 | 从图 02、29、32 整理科学机器、高礼帽和灵子分解器 |
| [烤桦木果](https://wiki.biligame.com/jikunhuangye/烤桦木果)及[烤绿蘑菇](https://wiki.biligame.com/jikunhuangye/烤绿蘑菇) | 2024-03-21 / 2024-02-23 | 保留火烤关系，单次用量和产量待核实 |
| 玩家实机制作栏截图 | 2026-11-24 核对 | 火炬材料用量 |
| [官方工具手册](https://www.taptap.cn/moment/867812280803266153)及[官方三维手册](https://www.taptap.cn/moment/865262413363022888?group_id=268439) | 2026-11-25 核对 | 开荒工具、黄金园艺锄的科技条件、三种料理的七组投料和恢复值 |
| [腾讯《饥荒科技手册》](https://jihuang.qq.com/cp/a20230420xjy/pc/page-news-detail.html?docid=9125582025783670033)及[官方种植指南](https://www.taptap.cn/moment/874293946451234011?group_id=268439) | 2026-11-24 核对 | 基础工具、开荒装备、科技和中间材料 |
| [4399 生存手册](https://a.4399.cn/starve/tools/collection)、[3DM 木甲攻略](https://shouyou.3dmgame.com/gl/634585.html)及[九游提灯攻略](https://www.9game.cn/news/12035613.html) | 2026-11-24 核对 | 工具配方、绳子产量和提灯科技条件 |

官方上线 FAQ 公布的客户端版本为 **1.30.1**。官方攻略记录链接到文章或对应配方图，图鉴核对日期与客户端版本分别记录。高礼帽、耕地机和便便桶的来源用量有出入，详情保留差异，合成树在该材料处停止展开。替身人偶另需消耗生命值，作为制作参考展示。[官方上线 FAQ](https://www.taptap.cn/moment/872603097178833842)

超出常见投料份数、含食材度数或替代写法、用量缺失和条件异常的料理保留原表配方作查询。空白属性留空。首版快照保留已核对的生命、饥饿、理智和部分烹饪时间，未补录保质期。可识别的保质期字段由更新脚本读取。材料按源表名称计算，例如「肉」和「小肉」分开计数。

### 数据使用与许可

核对了 [Wiki 首页](https://wiki.biligame.com/jikunhuangye/)和 MediaWiki 的站点许可信息，未找到该站可公开再分发的数据许可，API 返回的许可标题和链接均为空。BWIKI 社区规则要求站外转载用户内容先取得权利人许可。项目随附本地查询所需的配方事实和数值，没有附上攻略正文、游戏图标或 Wiki 截图。公开托管前请确认计划随站发布的数据是否有相应使用权限。[BWIKI 社区规则](https://wiki.biligame.com/wiki/WIKI社区规则)

页首图由内置图像生成工具绘制，资产在 src/assets/camp.png。生成设定为深绿针叶林、月亮与篝火营地，以复古野外手册风格绘制，左侧留出深色标题区。

## 更新数据

更新脚本单独使用 Python 3.10+ 和 Beautiful Soup。平时用网页无需 Python。脚本默认将制造、装备、食物、道具四张图鉴解析到项目根目录的 .wiki-candidate.json。候选文件带着来源链接、修订号和核对日期，方便比对。

~~~powershell
py -3 -m pip install beautifulsoup4
npm.cmd run data:wiki
~~~

如果 Wiki 的直接请求返回 567 或其他访问错误，可以在浏览器正常打开图鉴并保存为 HTML。把文件命名为 制造图鉴.html、装备图鉴.html、食物图鉴.html、道具图鉴.html，放入同一个目录，例如 wiki-html。

~~~powershell
npm.cmd run data:wiki -- --html-dir .\wiki-html
~~~

核对候选文件的条数、修订号及用量变化后，将候选文件复制到 src/data/wiki.json。脚本遇到识别不到的表格、列变化或重名会报错，现有数据仍可使用。初版快照来自此次成功读取的表格；随后在线脚本读取遇到了 567。

攻略和游戏内核对结果放在 src/data/supplement.json。只查到名称或来源用量有出入时将 ingredients 设为 null，条目仍可搜索。更新同名条目时，name 和 kind 一致会覆盖 Wiki 原条目。kind 用 craft 或 cook。ingredients 每项使用 item 和正整数 quantity，output 填单次产量。technology 省略表示未知，空数组表示无需科技，其他值为所需的科技名称。source 指向 sources 中的出处，sourceUrl 可指向单条图鉴详情。实机来源的 evidence 为 game，攻略来源为 guide。gameVersion 和 updated 在版本及日期可确认时填写。

运行 `py -3 -X utf8 scripts/update-handbook.py` 可从 4399 公开页面生成 `.handbook-candidate.json`。核对条目增减、材料数量、同物异名与来源链接后，可将候选文件更新到 `src/data/handbook.json`。读不到完整材料行、同条材料重复或自引用的配方跳过；未知科技和单次产量留空。4399 社区数据仅补充已有目录，已收录的同名记录优先。批量转载许可尚未确认，快照只整理事实字段，各条保留详情链接。[4399 版权声明](https://www.4399.com/notice/banquan.htm)

## Cloudflare Pages

推送到 `main` 后，GitHub Actions 使用 `.node-version` 中的 Node 版本安装依赖、构建静态文件，然后用 Wrangler 将 `dist` 发布到现有的 Pages 项目。也可在 Actions 的「部署荒野合成手册」中选择 `main` 手动运行。

在仓库 Settings → Secrets and variables → Actions 中设置 Secret `CLOUDFLARE_API_TOKEN`（目标账户的 Cloudflare Pages 编辑权限）和 Variable `CLOUDFLARE_ACCOUNT_ID`（该账户的 ID）。发布使用 `.github/workflows/deploy-pages.yml`。

| Pages 设置 | 值 |
| --- | --- |
| 根目录 | 项目根目录，包含 package.json |
| 框架 | Vue / Vite |
| 构建命令 | npm run build |
| 输出目录 | dist |
| Node.js | 22 |

本地生成 dist 时，在项目目录执行 npm.cmd run build；如需预览静态产物，执行 npm.cmd run preview。生产项目为 `jikunhuangye-helper`，生产分支为 `main`。[线上手册](https://huangye.lelenews.com/) · [Cloudflare Pages 构建配置](https://developers.cloudflare.com/pages/configuration/build-configuration/)
