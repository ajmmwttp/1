"""Pine v6 の10ファイルを共通部品から組み立てる: python -m research.turn_zones.build_pine

見た目・ゾーン判定・ラベル・状態表・アラートは10本とも同じ部品を使い,
各インジケーター固有の計算 (CORES) だけを差し替える. 出力先は pine/.
"""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
PINE = os.path.normpath(os.path.join(ROOT, "pine"))

HEAD = """//@version=6
// ============================================================================
// {title}
// 要素: {element}　種類: {kind}
// {about}
// 読み方: メインラインが赤の「高値圏ライン」を上抜け → 高値圏突入 / 緑の「安値圏ライン」を下抜け → 安値圏突入.
//         ゾーンから戻ったら離脱(小さな▼▲). ラベルとアラートは足の確定時だけ出る(リペイントなし).
// 既定値: TQQQ などの3倍レバETFの日足向け. 検証: research/turn_zones (NASDAQ×3合成 1999-2018).
// ============================================================================
indicator('{title}', shorttitle='{tag}', overlay=false, precision=0, max_labels_count=500, max_bars_back=1000)

// ---- 色 ----
color C_RED  = #d32f2f
color C_ORG  = #f57c00
color C_GRY  = #9e9e9e
color C_LGRN = #66bb6a
color C_GRN  = #2e7d32

// ---- 共通入力 ----
GV = '表示'
GL = 'ライン'
lw       = input.int(2, 'メインラインの太さ', minval=1, maxval=4, group=GV)
showIn   = input.bool(true, '突入ラベル', group=GV)
showOut  = input.bool({show_out}, '離脱の印(▼▲)', group=GV)
cool     = input.int({cool}, '同じ側の突入ラベルの間隔(本)', minval=0, group=GV)
showFill = input.bool(true, 'ライン超えの塗り', group=GV)
showBg   = input.bool(false, 'ゾーン中の背景色', group=GV)
showTbl  = input.bool(true, '状態テーブル', group=GV)
tblPosS  = input.string('右上', 'テーブル位置', options=['右上', '右下', '左上', '左下'], group=GV)
tblSizeS = input.string('小', 'テーブル文字', options=['小', '中', '大'], group=GV)
hyst     = input.float(0.0, '離脱の遊び(0=なし)', minval=0.0, maxval=30.0, group=GL)
"""

HELPERS = {
    "ema": """
// 指数移動平均. 最初の非na値で初期化し, naが来たら次の値で初期化し直す (毎バー必ず呼ぶこと)
f_ema(float x, simple int n) =>
    var float s = na
    float a = 2.0 / (n + 1)
    s := na(s) ? x : a * x + (1.0 - a) * s
    s
""",
    "rma": """
// Wilder の移動平均 (α=1/n). 初期化は f_ema と同じ
f_rma(float x, simple int n) =>
    var float s = na
    s := na(s) ? x : x / n + (1.0 - 1.0 / n) * s
    s
""",
    "tanh": """
f_tanh(float x) =>
    float e = math.exp(-2.0 * math.abs(x))
    math.sign(x) * (1.0 - e) / (1.0 + e)
""",
    "ss": """
// Ehlers 2極 SuperSmoother. 最初の2本は入力をそのまま返す
f_ss(float x, simple int P) =>
    float a1 = math.exp(-math.sqrt(2.0) * math.pi / P)
    float c2 = 2.0 * a1 * math.cos(math.sqrt(2.0) * math.pi / P)
    float c3 = -a1 * a1
    float c1 = 1.0 - c2 - c3
    var float y1 = na
    var float y2 = na
    var float x1 = na
    var int k = 0
    float y = k < 2 ? x : c1 * (x + x1) / 2.0 + c2 * y1 + c3 * y2
    y2 := y1
    y1 := y
    x1 := x
    k += 1
    y
""",
    "pnr": """
// 直近 n 個(当日を含む)を昇順に並べた ceil(p*n/100) 番目. n 個たまるまでは na
f_pnr(float x, simple int n, float p) =>
    var array<float> buf = array.new<float>()
    if not na(x)
        buf.push(x)
        if buf.size() > n
            buf.shift()
    float r = na
    if buf.size() == n
        array<float> srt = buf.copy()
        srt.sort(order.ascending)
        r := srt.get(int(math.ceil(p * n / 100.0)) - 1)
    r
""",
}

# E5/E6 共通: 過去データだけで判定するスイング検出. x(=ln close) を先に宣言してから置く
SWING = """
// ---- スイング検出 (未来は使わない): 極値から θ = k×対数ATR 戻したらスイング確定 ----
f_logatr(simple int n) =>
    float trL = na(close[1]) ? math.log(high) - math.log(low) : math.max(math.log(high) - math.log(low), math.abs(math.log(high) - math.log(close[1])), math.abs(math.log(low) - math.log(close[1])))
    var float s = na
    var float acc = 0.0
    var int cnt = 0
    if na(s)
        acc += trL
        cnt += 1
        if cnt == n
            s := acc / n
    else
        s += (trL - s) / n
    s

// v が過去の値 a_j より大きい度合い (なめらかなパーセンタイル, 0..1)
f_kcdf(float v, array<float> a, float rho, float c0) =>
    float acc = 0.0
    for aj in a
        acc += 1.0 / (1.0 + math.exp(-math.max(-50.0, math.min(50.0, (v - aj) / (rho * aj + c0)))))
    acc / a.size()

// [fromBar, 今] の中で最初に現れる x の最大(最小)とその足. 最大999本前まで
// 注意: 条件付きで呼ぶが, 読むのはグローバル系列 x の履歴なので値は正しい.
//       x を引数に変えないこと (エディタに「毎回呼ぶべき」という黄色い警告が出ても無視してよい)
f_scan(int fromBar, bool wantMax) =>
    int n = math.min(bar_index - fromBar, 999)
    float bv = x[n]
    int bb = bar_index - n
    if n > 0
        for j = 1 to n
            int i = n - j
            float vi = x[i]
            if wantMax ? vi > bv : vi < bv
                bv := vi
                bb := bar_index - i
    [bv, bb]

type Swing
    int dir = 0
    float pX
    int pB
    float eX
    int eB
    float cX
    int cB
    float hX
    int hB
    float hcX
    int hcB
    float lX
    int lB
    float lcX
    int lcB
    array<float> dU
    array<float> dD
    array<float> aU
    array<float> aD

method step(Swing s, float v, float h, int keep) =>
    if not na(h) and not na(v)
        if s.dir == 0
            if na(s.hX)
                s.hX := v
                s.hB := bar_index
                s.hcX := v
                s.hcB := bar_index
                s.lX := v
                s.lB := bar_index
                s.lcX := v
                s.lcB := bar_index
            else
                if v > s.hX
                    s.hX := v
                    s.hB := bar_index
                    s.hcX := v
                    s.hcB := bar_index
                else if v < s.hcX
                    s.hcX := v
                    s.hcB := bar_index
                if v < s.lX
                    s.lX := v
                    s.lB := bar_index
                    s.lcX := v
                    s.lcB := bar_index
                else if v > s.lcX
                    s.lcX := v
                    s.lcB := bar_index
            if s.hX - v >= h
                s.dir := -1
                s.pX := s.hX
                s.pB := s.hB
                s.eX := s.hcX
                s.eB := s.hcB
                [cv, cb] = f_scan(s.eB, true)
                s.cX := cv
                s.cB := cb
            else if v - s.lX >= h
                s.dir := 1
                s.pX := s.lX
                s.pB := s.lB
                s.eX := s.lcX
                s.eB := s.lcB
                [cv, cb] = f_scan(s.eB, false)
                s.cX := cv
                s.cB := cb
        else
            int d = s.dir
            if d * (v - s.eX) > 0
                s.eX := v
                s.eB := bar_index
                s.cX := v
                s.cB := bar_index
            else if d * (v - s.cX) < 0
                s.cX := v
                s.cB := bar_index
            if d * (s.eX - v) >= h
                array<float> D = d == 1 ? s.dU : s.dD
                array<float> A = d == 1 ? s.aU : s.aD
                D.push(float(s.eB - s.pB))
                A.push(math.abs(s.eX - s.pX))
                if D.size() > keep
                    D.shift()
                    A.shift()
                s.pX := s.eX
                s.pB := s.eB
                s.eX := s.cX
                s.eB := s.cB
                [cv, cb] = f_scan(s.eB, d == 1)
                s.cX := cv
                s.cB := cb
                s.dir := -d
    s
"""

TAIL = """
// ======== ここから下は10本共通 ========

// ---- ゾーン判定 (Python の zones() と同じ) ----
var int zone  = 0          // 1=高値圏, -1=安値圏, 0=中立
var int zBars = 0
var int lastTopLbl = na
var int lastBotLbl = na
int prevZ = zone
int newZ  = zone
if not na(osc) and not na(U) and not na(L)
    if zone == 1 and osc <= U - hyst
        newZ := 0
    else if zone == -1 and osc >= L + hyst
        newZ := 0
    if newZ == 0
        newZ := osc > U ? 1 : osc < L ? -1 : 0
bool topIn  = newZ == 1 and prevZ != 1
bool topOut = prevZ == 1 and newZ != 1
bool botIn  = newZ == -1 and prevZ != -1
bool botOut = prevZ == -1 and newZ != -1
zBars := newZ == 0 ? 0 : newZ == prevZ ? zBars + 1 : 1
zone  := newZ

// ---- 描画 ----
color oscCol = na(osc) ? na : osc > U ? C_RED : osc < L ? C_GRN : osc >= 0 ? color.from_gradient(osc, 0.3 * U, U, C_GRY, C_ORG) : color.from_gradient(osc, L, 0.3 * L, C_LGRN, C_GRY)
pOsc = plot(osc, 'メインライン', color=oscCol, linewidth=lw)
pU   = plot(U, '高値圏ライン', color=C_RED, linewidth=1, display=display.pane)
pL   = plot(L, '安値圏ライン', color=C_GRN, linewidth=1, display=display.pane)
pTop = plot(100, '上端', color=color.new(C_RED, 100), display=display.pane, editable=false)
pBot = plot(-100, '下端', color=color.new(C_GRN, 100), display=display.pane, editable=false)
hline(0, '0', color=color.new(C_GRY, 50), linestyle=hline.style_dotted)
fill(pU, pTop, color=color.new(C_RED, 94), title='高値圏の帯')
fill(pL, pBot, color=color.new(C_GRN, 94), title='安値圏の帯')
fill(pOsc, pU, color=showFill and osc > U ? color.new(C_RED, 62) : na, title='高値圏の塗り')
fill(pOsc, pL, color=showFill and osc < L ? color.new(C_GRN, 62) : na, title='安値圏の塗り')
bgcolor(showBg and zone == 1 ? color.new(C_RED, 93) : showBg and zone == -1 ? color.new(C_GRN, 93) : na, title='ゾーン背景')

// ---- ラベル (確定足のみ). ライン上に付け, 本体は中立側に出すので画面外に切れない ----
// 間隔(cool)で突入ラベルを省いたゾーンは, 離脱の印も出さない (離脱を先に処理するので反転した足でも正しい)
var bool topLbld = true
var bool botLbld = true
if barstate.isconfirmed
    if topOut and showOut and topLbld
        label.new(bar_index, U, '', style=label.style_triangledown, color=color.new(C_RED, 30), size=size.tiny)
    if botOut and showOut and botLbld
        label.new(bar_index, L, '', style=label.style_triangleup, color=color.new(C_GRN, 30), size=size.tiny)
    if topIn
        topLbld := not showIn or na(lastTopLbl) or bar_index - lastTopLbl > cool
        if showIn and topLbld
            label.new(bar_index, U, '高値圏突入' + sfxTop, style=label.style_label_up, color=C_RED, textcolor=color.white, size=size.small)
            lastTopLbl := bar_index
    if botIn
        botLbld := not showIn or na(lastBotLbl) or bar_index - lastBotLbl > cool
        if showIn and botLbld
            label.new(bar_index, L, '安値圏突入' + sfxBot, style=label.style_label_down, color=C_GRN, textcolor=color.white, size=size.small)
            lastBotLbl := bar_index

// ---- 状態テーブル ----
var table tb = table.new(tblPosS == '右上' ? position.top_right : tblPosS == '右下' ? position.bottom_right : tblPosS == '左上' ? position.top_left : position.bottom_left, 1, 1)
if showTbl and barstate.islast
    string tsz = tblSizeS == '大' ? size.large : tblSizeS == '中' ? size.normal : size.small
    string st  = zone == 1 ? '高値圏 ' + str.tostring(zBars) + '本目' : zone == -1 ? '安値圏 ' + str.tostring(zBars) + '本目' : na(osc) ? '計算中' : osc >= 0.75 * U ? '上ライン接近' : osc <= 0.75 * L ? '下ライン接近' : '中立'
    string ds  = na(osc) ? '' : zone == 1 and osc > U ? ' / 上ライン超え +' + str.tostring(osc - U, '#') : zone == -1 and osc < L ? ' / 下ライン超え ' + str.tostring(osc - L, '#') : zone != 0 ? ' / 離脱の遊びの中' : osc >= 0 ? ' / 上ラインまで ' + str.tostring(U - osc, '#') : ' / 下ラインまで ' + str.tostring(osc - L, '#')
    string pv  = barstate.isconfirmed ? '' : '（確定前）'
    color tc   = zone == 1 ? C_RED : zone == -1 ? C_GRN : chart.fg_color
    table.cell(tb, 0, 0, '【{tag}】状態: ' + st + ds + pv + note, text_color=tc, text_size=tsz, bgcolor=color.new(chart.bg_color, 20))

// ---- アラート (確定足のみ. アラート作成時は「バーの終値で1回」を選ぶ) ----
alertcondition(topIn and barstate.isconfirmed, '高値圏突入', '{{{{ticker}}}} {tag} 高値圏突入')
alertcondition(topOut and barstate.isconfirmed, '高値圏離脱', '{{{{ticker}}}} {tag} 高値圏離脱')
alertcondition(botIn and barstate.isconfirmed, '安値圏突入', '{{{{ticker}}}} {tag} 安値圏突入')
alertcondition(botOut and barstate.isconfirmed, '安値圏離脱', '{{{{ticker}}}} {tag} 安値圏離脱')
alertcondition((topIn or topOut or botIn or botOut) and barstate.isconfirmed, 'ゾーン変化(いずれか)', '{{{{ticker}}}} {tag} ゾーン変化')
if barstate.isconfirmed and (topIn or topOut or botIn or botOut)
    string evt = topOut and botIn ? '高値圏離脱→安値圏突入' : botOut and topIn ? '安値圏離脱→高値圏突入' : topIn ? '高値圏突入' : topOut ? '高値圏離脱' : botIn ? '安値圏突入' : '安値圏離脱'
    alert(syminfo.ticker + ' {tag} ' + evt + ' 値=' + str.tostring(osc, '#'), alert.freq_once_per_bar_close)
"""

# 各インジケーター固有の計算. 必須: float osc(-100..100), float U, float L, string sfxTop, sfxBot, note
CORES = {
    "E1": dict(
        title="E1 回帰トレンド乖離", tag="E1乖離", element="乖離（平均からの行き過ぎ）", kind="先行（吹き上げ・投げの終盤）",
        file="E01_regression_kairi.pine", helpers=["ema", "tanh"],
        about="直近75本の対数回帰線から終値がどれだけ外れたかを, 回帰の普段のブレ幅(残差σ)で測る. トレンドに沿っている間は0付近.",
        code="""
G1 = '計算'
n    = input.int(75, '回帰期間(本)', minval=40, maxval=300, group=G1)
smE  = input.int(5, '仕上げEMA', minval=1, group=G1)
kU   = input.float(2.3, '上側スケール', minval=0.5, step=0.1, group=G1)
kD   = input.float(2.6, '下側スケール', minval=0.5, step=0.1, group=G1)
U    = input.float(60.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='線がこの値を上抜けたら高値圏突入. +60 ≒ トレンド線から普段のブレ幅の約1.6倍上')
L    = input.float(-60.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='線がこの値を下抜けたら安値圏突入. -60 ≒ トレンド線から普段のブレ幅の約1.8倍下')
float y    = math.log(close)
float fit  = ta.linreg(y, n, 0)
float b    = fit - ta.linreg(y, n, 1)          // 回帰の傾き
float vy   = ta.variance(y, n, true)            // 母分散 (biased)
float sres = na(vy) or na(b) ? na : math.sqrt(math.max(vy - b * b * (n * n - 1) / 12.0, 0.0))
float zc   = na(sres) ? na : sres > 0 ? (y - fit) / sres : 0.0
float zsm  = f_ema(zc, smE)
float osc  = na(zsm) ? na : 100.0 * f_tanh(zsm / (zsm >= 0 ? kU : kD))
string sfxTop = ''
string sfxBot = ''
string note = ''
"""),
    "E2": dict(
        title="E2 勢いバランス（短期TSI）", tag="E2勢い", element="勢い（上昇と下落の強さ）", kind="先行（極値の約2本前）",
        file="E02_tsi_balance.pine", helpers=["ema", "pnr"],
        about="直近の上げ幅と下げ幅の綱引き(TSI 6/3). ラインは自身の過去120本の90%/10%点で自動調整(35〜75の範囲).",
        code="""
G1 = '計算'
r1   = input.int(6, '1段目EMA', minval=2, group=G1)
r2   = input.int(3, '2段目EMA', minval=1, group=G1)
mode = input.string('自動調整', 'ラインの種類', options=['自動調整', '固定'], group=GL)
fixT = input.float(55.0, '固定ライン ±', minval=10.0, maxval=95.0, group=GL, tooltip='「固定」のときと, 自動調整の準備が整うまでのライン')
adN  = input.int(120, '自動調整: 期間(本)', minval=30, maxval=500, group=GL, tooltip='この本数の線の値の上位10%/下位10%の境目をラインにする (35〜75 の範囲)')
adP  = input.float(90.0, '自動調整: 上側パーセント', minval=60.0, maxval=99.0, group=GL)
float pc  = nz(ta.change(close))
float num = f_ema(f_ema(pc, r1), r2)
float den = f_ema(f_ema(math.abs(pc), r1), r2)
float osc = den > 0 ? math.max(-100.0, math.min(100.0, 100.0 * num / den)) : 0.0
float pu  = f_pnr(osc, adN, adP)
float pl  = f_pnr(osc, adN, 100.0 - adP)
bool  fx  = mode == '固定'
float U   = fx or na(pu) ? fixT : math.max(35.0, math.min(75.0, pu))
float L   = fx or na(pl) ? -fixT : math.min(-35.0, math.max(-75.0, pl))
string sfxTop = ''
string sfxBot = ''
string note = not fx and na(pu) ? ' / 自動調整の準備中(固定±' + str.tostring(fixT, '#') + ')' : ''
"""),
    "E3": dict(
        title="E3 失速率", tag="E3失速", element="加速・失速（勢いの変化）", kind="確認寄り（極値の0〜1本後）",
        file="E03_speed_retention.pine", helpers=["ema", "rma", "ss"],
        about="今の上昇(下落)で一番速かった時から, 速度がどれだけ落ちたか. 加速中は0付近, 失速すると±に伸びる.",
        code="""
G1 = '計算'
P    = input.int(4, '速度の平滑期間', minval=2, group=G1)
sigN = input.int(100, '平均速度の期間', minval=20, group=G1)
flr  = input.float(1.0, '小さな脚のフロア(σ倍)', minval=0.1, step=0.1, group=G1)
post = input.int(3, '仕上げEMA', minval=1, group=G1)
T    = input.float(45.0, 'ライン ±', minval=10.0, maxval=95.0, group=GL, tooltip='±45 = 今の上昇(下落)の最高速度から45%以上減速したら突入')
float r   = nz(math.log(close / close[1]))
float v   = f_ss(r, P)
float sig = f_rma(math.abs(v), sigN)
var int   side = 0
var float pk   = 0.0
int s = v > 0 ? 1 : v < 0 ? -1 : side == 0 ? 1 : side
if s != side
    side := s
    pk   := math.abs(v)
else
    pk   := math.max(pk, math.abs(v))
float den = math.max(pk, flr * sig)
float raw = den > 0 ? side * (pk - math.abs(v)) / den : 0.0
float osc = f_ema(100.0 * raw, post)
float U = T
float L = -T
string sfxTop = '(失速)'
string sfxBot = '(失速)'
string note = ''
"""),
    "E4": dict(
        title="E4 出来高重心", tag="E4出来高", element="出来高（資金の流れ）", kind="状況（2〜5本前から警戒）",
        file="E04_volume_cog.pine", helpers=["ema", "rma", "tanh"],
        about="直近10本の大商いが高い価格帯と安い価格帯のどちらに集まったか. 高値帯で大商い=天井警戒, 安値帯で大商い=底警戒.",
        code="""
G1 = '計算'
lenV    = input.int(10, '期間(EMA)', minval=2, group=G1)
atrLen  = input.int(14, 'ATR期間', minval=1, group=G1)
normLen = input.int(252, '正規化期間(本)', minval=50, group=G1)
kk      = input.float(1.5, 'スケール', minval=0.1, step=0.1, group=G1)
useDV   = input.bool(true, '売買代金(出来高×終値)で計算', group=G1)
U       = input.float(60.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='高値帯で大商いが続くと上抜ける (天井警戒)')
L       = input.float(-60.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='安値帯で大商いが続くと下抜ける (底警戒)')
float v    = nz(volume) * (useDV ? close : 1.0)
float wv   = v > 0 ? 1.0 : 0.0                 // 出来高の無い足(na/0)は, 出来高の重心にも価格の平均にも入れない
float evh  = f_ema(v * hlc3, lenV)
float ev   = f_ema(v, lenV)
float ewh  = f_ema(wv * hlc3, lenV)
float ew   = f_ema(wv, lenV)
float atr  = f_rma(ta.tr(true), atrLen)
float raw  = ev > 0 and ew > 0 and atr > 0 ? (evh / ev - ewh / ew) / atr : 0.0
var int nV = 0
nV += v > 0 ? 1 : 0
float rms  = math.sqrt(ta.sma(raw * raw, normLen))
float oscC = rms > 0 and nV >= normLen ? 100.0 * f_tanh(raw / rms / kk) : na
// 足の途中は出来高がまだ途中なので, 確定するまで前の足の値を出す (確定した足の値は変わらない)
float osc  = barstate.isconfirmed ? oscC : oscC[1]
string sfxTop = '(出来高)'
string sfxBot = '(出来高)'
string note = (nV == 0 ? ' / この銘柄には出来高データがありません' : '') + (barstate.isconfirmed ? '' : ' / 確定まで前の足の値')
"""),
    "E5": dict(
        title="E5 日柄成熟度（大波）", tag="E5日柄", element="日柄（時間）", kind="先行（最後の新値の足で山）",
        file="E05_swing_age_maturity.pine", helpers=[], swing=True,
        about="今の大きな波が, 過去8回の同じ向きの大波と比べて日数的にどれだけ成熟したか. 新値が止まると数本でしぼむ.",
        pre="""
G1 = '計算'
k    = input.float(3.0, 'スイング確定幅 k(×対数ATR)', minval=1.0, step=0.1, group=G1)
nAtr = input.int(50, '対数ATR期間', minval=10, group=G1)
K    = input.int(8, '比較する過去スイング数', minval=3, group=G1)
Kmin = input.int(3, '必要スイング数', minval=1, group=G1)
tau  = input.float(4.0, '更新停止の減衰(本)', minval=0.5, group=G1)
U    = input.float(70.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='+70 ≒ 今の上げの波が, 過去の上げの大波の約7割より長く続いていて, まだ新値を取っている')
L    = input.float(-70.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='-70 ≒ 今の下げの波が, 過去の下げの大波の約7割より長く続いていて, まだ新安値を取っている')
float x  = math.log(close)
""",
        code="""
float th = k * f_logatr(nAtr)
var Swing sw = Swing.new(dU=array.new<float>(), dD=array.new<float>(), aU=array.new<float>(), aD=array.new<float>())
sw.step(x, th, K)
float osc = na
if sw.dir != 0
    array<float> Ds = sw.dir == 1 ? sw.dU : sw.dD
    if Ds.size() >= math.min(Kmin, K)
        osc := 100.0 * sw.dir * f_kcdf(float(sw.eB - sw.pB), Ds, 0.15, 1.0) * math.exp(-math.pow((bar_index - sw.eB) / tau, 2))
string sfxTop = '(日柄)'
string sfxBot = '(日柄)'
string note = ''
"""),
    "E6": dict(
        title="E6 値幅達成率", tag="E6値幅", element="値幅（スイングの大きさ）", kind="先行（新値の足で山）",
        file="E06_swing_extension_pct.pine", helpers=[], swing=True,
        about="今の波の値幅が, 過去8回の同じ向きの波の何割より大きいか. 極値から押す(戻す)と0へ戻る.",
        pre="""
G1 = '計算'
k    = input.float(2.0, 'スイング確定幅 k(×対数ATR)', minval=0.5, step=0.1, group=G1)
nAtr = input.int(50, '対数ATR期間', minval=10, group=G1)
K    = input.int(8, '比較する過去スイング数', minval=3, group=G1)
Kmin = input.int(3, '必要スイング数', minval=1, group=G1)
hand = input.float(0.8, '0に戻る戻り幅(×θ)', minval=0.2, maxval=1.0, step=0.1, group=G1)
U    = input.float(70.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='+70 ≒ 今の上げ幅が過去8回の上げの波の約7割より大きく, 高値の近くにいる')
L    = input.float(-55.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='-55 ≒ 今の下げ幅が過去8回の下げの波の半分以上より大きく, 安値の近くにいる')
float x  = math.log(close)
""",
        code="""
float th = k * f_logatr(nAtr)
var Swing sw = Swing.new(dU=array.new<float>(), dD=array.new<float>(), aU=array.new<float>(), aD=array.new<float>())
sw.step(x, th, K)
float raw = na
if sw.dir != 0
    array<float> As = sw.dir == 1 ? sw.aU : sw.aD
    if As.size() >= math.min(Kmin, K)
        float u = math.max(0.0, math.min(1.0, sw.dir * (sw.eX - x) / (hand * th)))
        raw := 100.0 * sw.dir * f_kcdf(math.abs(sw.eX - sw.pX), As, 0.15, 0.0) * (1.0 - u)
float osc = (3.0 * raw + 2.0 * raw[1] + raw[2]) / 6.0
string sfxTop = '(値幅)'
string sfxBot = '(値幅)'
string note = ''
"""),
    "E7": dict(
        title="E7 サイクル位相", tag="E7周期", element="周期（サイクルの位相）", kind="先行（山の2〜3本前に突入）",
        file="E07_cycle_phase.pine", helpers=[],
        about="直近20本の値動きを1周期の波(cos)と照らし合わせて, サイクルの中で今どこにいるかを読む. トレンド中は0付近.",
        code="""
G1 = '計算'
P  = input.int(20, 'サイクル長 P', minval=6, maxval=120, group=G1, tooltip='想定するサイクルの長さ(本). TQQQ 日足は20前後, SOXL は16〜18, SPXL は20〜24 が目安')
z0 = input.float(0.5, '位相確度の下限', minval=0.05, maxval=1.0, step=0.05, group=G1, tooltip='波の形がはっきりしない時に線を0へ寄せる強さ')
U  = input.float(85.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='+85 ≒ サイクルの山の前後 約2本以内')
L  = input.float(-85.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='-85 ≒ サイクルの谷の前後 約2本以内')
float nn  = P
float sx  = 0.0
float sxx = 0.0
float sc  = 0.0
float scc = 0.0
float sxc = 0.0
float ss  = 0.0
float sss = 0.0
float sxs = 0.0
for i = 0 to P - 1
    float xv = math.log(close[i])
    float cv = math.cos(2.0 * math.pi * i / P)
    float sv = -math.sin(2.0 * math.pi * i / P)
    sx  += xv
    sxx += xv * xv
    sc  += cv
    scc += cv * cv
    sxc += xv * cv
    ss  += sv
    sss += sv * sv
    sxs += xv * sv
float vx  = nn * sxx - sx * sx
float re  = vx > 0 ? (nn * sxc - sx * sc) / math.sqrt(vx * (nn * scc - sc * sc)) : 0.0
float im  = vx > 0 ? (nn * sxs - sx * ss) / math.sqrt(vx * (nn * sss - ss * ss)) : 0.0
float mag = math.sqrt(re * re + im * im)
float osc = bar_index < P - 1 ? na : 100.0 * re / math.max(mag, z0)
string sfxTop = '(周期)'
string sfxBot = '(周期)'
string note = ''
"""),
    "E8": dict(
        title="E8 高値・安値切り上げ連続", tag="E8連続", element="連続（カウント・疲弊）", kind="先行（極値の足）",
        file="E08_hhhl_streak.pine", helpers=[],
        about="高値・安値の切り上げ(切り下げ)が何日続いたかの階段. 5日連続で上限. 途切れると1本ごとに半分になる.",
        code="""
G1 = '計算'
N   = input.int(5, '飽和カウント', minval=2, maxval=15, group=G1, tooltip='この日数続いたら最大(±100)とみなす')
rho = input.float(0.5, '途切れ後に残す割合', minval=0.0, maxval=0.9, step=0.1, group=G1, tooltip='連続が途切れた後, 1本ごとに前の値のこの割合を残す. 大きいほどゆっくり下がる')
U   = input.float(65.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='+65 ≒ 高値と安値の切り上げが, 合わせて約3〜4日以上続いている')
L   = input.float(-65.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='-65 ≒ 高値と安値の切り下げが, 合わせて約3〜4日以上続いている')
f_runLen(bool cnd) =>
    var int r = 0
    r := cnd ? r + 1 : 0
    r
f_hold(float f, float rr) =>
    var float m = 0.0
    m := math.max(f, rr * m)
    m
float nn = N
bool hh = bar_index >= 1 and high > high[1]
bool hl = bar_index >= 1 and low > low[1]
bool ll = bar_index >= 1 and low < low[1]
bool lh = bar_index >= 1 and high < high[1]
float cHH = f_hold(math.min(f_runLen(hh) / nn, 1.0), rho) - f_hold(math.min(f_runLen(ll) / nn, 1.0), rho)
float cHL = f_hold(math.min(f_runLen(hl) / nn, 1.0), rho) - f_hold(math.min(f_runLen(lh) / nn, 1.0), rho)
float osc = 100.0 * (cHH + cHL) / 2.0
string sfxTop = '(連続)'
string sfxBot = '(連続)'
string note = ''
"""),
    "E9": dict(
        title="E9 反転インパルス", tag="E9足形", element="ローソク足の形（ヒゲ・終値の位置）", kind="確認型（極値の翌足）",
        file="E09_reversal_impulse.pine", helpers=["ema", "tanh"], cool=5, show_out="false",
        about="高値引けが続いた後の安値引け(大陰線・包み足型), 安値引けが続いた後の高値引けを捉える. 天井・底の翌足で出る確認型.",
        code="""
G1 = '計算'
pLen  = input.int(8, '直前の引け圧力の期間', minval=2, group=G1)
sm    = input.int(3, '平滑EMA', minval=1, group=G1)
kS    = input.float(0.25, 'スケール', minval=0.05, step=0.05, group=G1)
U     = input.float(45.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='高値引けが続いた後に安値引けの足が出ると上抜ける (天井の確認)')
L     = input.float(-45.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='安値引けが続いた後に高値引けの足が出ると下抜ける (底の確認)')
float rng  = high - low
float clv  = rng > 0 ? (2.0 * close - high - low) / rng : 0.0
float pNum = f_ema(2.0 * close - high - low, pLen)
float pDen = f_ema(rng, pLen)
float pr   = pDen > 0 ? pNum / pDen : na
float prp  = pr[1]
float r    = na(prp) ? na : math.max(prp, 0.0) * math.max(-clv, 0.0) - math.max(-prp, 0.0) * math.max(clv, 0.0)
float sr   = f_ema(r, sm)
float osc  = bar_index < 20 ? na : 100.0 * f_tanh(sr / kS)     // 最初の20本は初期値の影響が大きいので出さない
string sfxTop = '(天井確認)'
string sfxBot = '(底確認)'
string note = ''
"""),
    "E10": dict(
        title="E10 恐怖・慢心ゲージ", tag="E10ボラ", element="値動きの荒さ（ボラティリティ）", kind="底は当日 / 天井側は慢心の警戒",
        file="E10_vol_term_gauge.pine", helpers=["ema", "rma", "tanh"],
        about="下げで値幅が急に広がる=恐怖(安値圏), 値幅が縮んで静かすぎる=慢心(高値圏). 高値圏は価格の天井そのものではなく警戒.",
        code="""
G1 = '計算'
fL  = input.int(3, '短期値幅 RMA', minval=1, group=G1)
sL  = input.int(30, '基準値幅 RMA', minval=5, group=G1)
gL  = input.int(5, '上下判定 EMA', minval=2, group=G1)
sh  = input.float(4.0, '上下判定の鋭さ', minval=0.5, group=G1)
wb  = input.float(0.5, '吹き上げの重み', minval=0.0, maxval=1.0, group=G1)
smL = input.int(3, '平滑EMA', minval=1, group=G1)
kUp = input.float(0.45, 'スケール上側(慢心)', minval=0.05, step=0.01, group=G1)
kDn = input.float(0.26, 'スケール下側(恐怖)', minval=0.05, step=0.01, group=G1)
U   = input.float(60.0, '高値圏ライン', minval=1, maxval=99, group=GL, tooltip='値幅が普段よりかなり縮んで静かすぎる (慢心). 価格の天井そのものではなく警戒')
L   = input.float(-60.0, '安値圏ライン', minval=-99, maxval=-1, group=GL, tooltip='下げで値幅が急に広がっている (恐怖). 底の当日に出やすい')
float tr0  = ta.tr(true)
float trp  = na(close[1]) ? na : tr0 / close[1]
float vf   = f_rma(trp, fL)
float vs   = f_rma(trp, sL)
float vr   = na(vf) or na(vs) ? na : vf > 0 and vs > 0 ? math.log(vf / vs) : 0.0
float r    = na(close[1]) ? 0.0 : math.log(close / close[1])
float up2  = f_ema(r > 0 ? r * r : 0.0, gL)
float dn2  = f_ema(r < 0 ? r * r : 0.0, gL)
float gate = up2 + dn2 > 0 ? f_tanh(sh * (dn2 - up2) / (up2 + dn2)) : 0.0
float w    = gate > 0 ? gate : wb * gate
float xx   = na(vr) ? na : vr > 0 ? -vr * w : -vr
float xs   = f_ema(xx, smL)
float osc  = na(xs) or bar_index < 5 * sL ? na : 100.0 * f_tanh(xs / (xs >= 0 ? kUp : kDn))   // 最初の 5×基準期間 は初期値の影響が大きい
string sfxTop = '(慢心)'
string sfxBot = '(恐怖)'
string note = ''
"""),
}


def build(key):
    c = CORES[key]
    out = HEAD.format(title=c["title"], tag=c["tag"], element=c["element"], kind=c["kind"], about=c["about"],
                      show_out=c.get("show_out", "true"), cool=c.get("cool", 3))
    out += "\n// ======== ここから " + c["tag"] + " 固有の計算 ========"
    out += c.get("pre", "")
    for h in c["helpers"]:
        out += HELPERS[h]
    if c.get("swing"):
        out += SWING
    out += c["code"]
    out += TAIL.replace("{tag}", c["tag"]).replace("{{{{ticker}}}}", "{{ticker}}")
    return c["file"], out


def main():
    os.makedirs(PINE, exist_ok=True)
    for key in CORES:
        name, text = build(key)
        with open(os.path.join(PINE, name), "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote", name, len(text.splitlines()), "lines")


if __name__ == "__main__":
    main()
