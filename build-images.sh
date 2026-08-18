#!/usr/bin/env bash
#
# 把 photos/ 里的原图预压成四档 webp，产物放在 photos/w96 w400 w800 w1200。
# 这四档对应 index.html 里 cdn() 被调用的四个宽度，缺一档那一档就图裂。
#
# 什么时候要跑：加了新照片、换了照片之后。跑完连同 photos/w*/ 一起 commit。
# 依赖：brew install webp
#
# 已经压过且原图没动过的会自动跳过，所以重复跑很快。
# 想全部重压：./build-images.sh --force

set -euo pipefail
cd "$(dirname "$0")"

SRC=photos
WIDTHS=(96 400 800 1200)
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

if ! command -v cwebp >/dev/null 2>&1; then
  echo "找不到 cwebp。先装一下："
  echo "  brew install webp"
  exit 1
fi

if [ ! -d "$SRC" ]; then
  echo "没有 $SRC 目录，是不是不在仓库根目录跑的？"
  exit 1
fi

for w in "${WIDTHS[@]}"; do mkdir -p "$SRC/w$w"; done

shopt -s nullglob nocaseglob
originals=("$SRC"/*.jpg "$SRC"/*.jpeg)
shopt -u nocaseglob

if [ ${#originals[@]} -eq 0 ]; then
  echo "$SRC 下没有 jpg，没事可做"
  exit 0
fi

built=0
skipped=0

for f in "${originals[@]}"; do
  name=$(basename "$f"); name="${name%.*}"

  # 原图实际宽度——比目标档窄就别放大，直接原尺寸转
  srcw=$(sips -g pixelWidth "$f" 2>/dev/null | awk '/pixelWidth/{print $2}')
  [ -z "$srcw" ] && srcw=999999

  for w in "${WIDTHS[@]}"; do
    out="$SRC/w$w/$name.webp"

    if [ $FORCE -eq 0 ] && [ -f "$out" ] && [ "$out" -nt "$f" ]; then
      skipped=$((skipped + 1))
      continue
    fi

    # 96 那档进页面就被 CSS 糊掉 16px，压狠一点没人看得出来
    q=80; [ "$w" = 96 ] && q=45

    if [ "$srcw" -gt "$w" ]; then
      cwebp -quiet -q "$q" -resize "$w" 0 "$f" -o "$out"
    else
      cwebp -quiet -q "$q" "$f" -o "$out"
    fi
    built=$((built + 1))
  done
done

echo "原图 ${#originals[@]} 张 · 新压 $built 个 · 跳过 $skipped 个（原图没变）"
echo
for w in "${WIDTHS[@]}"; do
  n=$(ls -1 "$SRC/w$w" 2>/dev/null | wc -l | tr -d ' ')
  printf "  w%-5s %3s 个  %s\n" "$w" "$n" "$(du -sh "$SRC/w$w" | cut -f1)"
done
echo
echo "原图合计 $(du -sh "$SRC"/*.jpg 2>/dev/null | awk '{s+=$1} END{print s}')KB（保留着，webp 挂了要靠它兜底）"

# 每档张数对不上就是有图没压到，页面上会表现为图裂
expect=${#originals[@]}
for w in "${WIDTHS[@]}"; do
  n=$(ls -1 "$SRC/w$w" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n" -ne "$expect" ]; then
    echo "⚠️  w$w 有 $n 个，原图有 $expect 张，对不上——检查一下是不是有重名或者删掉的老图残留"
  fi
done
