#!/usr/bin/env python3
"""Generate printable MARD 221 拼豆 pattern PDF.
Outputs: PREFIX.pdf, PREFIX_page*.png, PREFIX_preview.png, PREFIX_overview_grid.png, PREFIX_counts.csv
"""
import argparse, csv, json, math, os
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

def font(size, bold=False):
    fp = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(fp, size) if os.path.exists(fp) else ImageFont.load_default()

F = {}
def init_fonts():
    F.update({
        'title': font(48, True), 'h2': font(26, True), 'body': font(22),
        'small': font(18), 'tiny': font(13), 'code': font(12, True),
        'num': font(14, True), 'note': font(19)
    })

def load_palette(path):
    data = json.load(open(os.path.expanduser(path), encoding='utf-8'))['palette']
    return [(p['tag'], tuple(p['rgb']), p['hex'].upper()) for p in data]

def nearest(rgb, pal):
    r,g,b = rgb[:3]
    best = None; bestd = 10**12
    for tag,(pr,pg,pb),hx in pal:
        d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
        if d < bestd:
            bestd = d; best = (tag,(pr,pg,pb),hx)
    return best

def text(draw, xy, s, fill=(30,30,30), f=None, anchor=None):
    draw.text(xy, s, fill=fill, font=f or F['body'], anchor=anchor)

def rect(draw, box, outline=(80,80,80), width=1, fill=None):
    draw.rectangle(box, outline=outline, width=width, fill=fill)

def fit_image(im, box, bg=(255,255,255)):
    x0,y0,x1,y1 = box
    bw,bh = x1-x0, y1-y0
    canvas = Image.new('RGB', (bw,bh), bg)
    img = im.convert('RGB').copy()
    img.thumbnail((bw,bh), Image.Resampling.LANCZOS)
    canvas.paste(img, ((bw-img.width)//2, (bh-img.height)//2))
    return canvas

def make_grid_image(mapped, labels=False, start_r=0, start_c=0, rows=None, cols=None, cell=14, number_headers=False):
    if rows is None: rows = len(mapped)
    if cols is None: cols = len(mapped[0])
    header = 32 if number_headers else 0
    img = Image.new('RGB', (header + cols*cell + 1, header + rows*cell + 1), 'white')
    d = ImageDraw.Draw(img)
    if number_headers:
        d.rectangle([0,0,img.width-1, header-1], fill=(245,245,245))
        d.rectangle([0,0,header-1,img.height-1], fill=(245,245,245))
        for c in range(cols):
            d.text((header + c*cell + cell/2, header-6), str(start_c+c+1), font=F['num'], fill=(40,40,40), anchor='mb')
        for r in range(rows):
            d.text((header-6, header + r*cell + cell/2), str(start_r+r+1), font=F['num'], fill=(40,40,40), anchor='rm')
        d.line([header,0,header,img.height], fill=(90,90,90), width=2)
        d.line([0,header,img.width,header], fill=(90,90,90), width=2)
    for r in range(rows):
        for c in range(cols):
            item = mapped[start_r+r][start_c+c]
            x0 = header + c*cell; y0 = header + r*cell
            if item is None:
                rgb=(255,255,255); tag=''
            else:
                tag,rgb,hx = item
            d.rectangle([x0,y0,x0+cell,y0+cell], fill=rgb, outline=(185,185,185))
            if labels and item is not None:
                lum = 0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2]
                fg = (0,0,0) if lum > 155 else (255,255,255)
                shadow = (255,255,255) if fg == (0,0,0) else (0,0,0)
                d.text((x0+cell/2+0.5, y0+cell/2+0.5), tag, font=F['code'], fill=shadow, anchor='mm')
                d.text((x0+cell/2, y0+cell/2), tag, font=F['code'], fill=fg, anchor='mm')
    for c in range(cols+1):
        x = header + c*cell
        if c % 10 == 0:
            d.line([x, header, x, header+rows*cell], fill=(45,45,45), width=3)
        elif c % 5 == 0:
            d.line([x, header, x, header+rows*cell], fill=(80,80,80), width=2)
    for r in range(rows+1):
        y = header + r*cell
        if r % 10 == 0:
            d.line([header, y, header+cols*cell, y], fill=(45,45,45), width=3)
        elif r % 5 == 0:
            d.line([header, y, header+cols*cell, y], fill=(80,80,80), width=2)
    return img

def paste_fit(page, im, box):
    page.paste(fit_image(im, box), (box[0], box[1]))

def sorted_tags(tags):
    def k(tag):
        return (tag[0], int(tag[1:]) if tag[1:].isdigit() else 999)
    return sorted(tags, key=k)

def build(args):
    init_fonts()
    pal = load_palette(args.palette)
    bytag = {tag:(rgb,hx) for tag,rgb,hx in pal}
    orig = Image.open(args.image).convert('RGBA')
    w = args.width
    h = args.height or max(1, round(orig.height * w / orig.width))
    small = orig.resize((w,h), Image.Resampling.LANCZOS).convert('RGBA')
    mapped=[]; counts=Counter(); empty_count=0
    for y in range(h):
        row=[]
        for x in range(w):
            rgba = small.getpixel((x,y))
            if args.empty_white_threshold is not None and min(rgba[:3]) >= args.empty_white_threshold:
                row.append(None); empty_count += 1; continue
            tag,rgb,hx = nearest(rgba[:3], pal)
            row.append((tag,rgb,hx)); counts[tag] += 1
        mapped.append(row)
    preview = Image.new('RGB',(w,h),'white')
    for y,row in enumerate(mapped):
        for x,item in enumerate(row):
            if item is not None: preview.putpixel((x,y), item[1])
    preview_big = preview.resize((max(1,w*10), max(1,h*10)), Image.Resampling.NEAREST)
    overview_grid = make_grid_image(mapped, cell=max(6, min(14, 900//max(w,h))), labels=False)
    prefix = args.out
    preview_big.save(prefix + '_preview.png')
    overview_grid.resize((overview_grid.width*2, overview_grid.height*2), Image.Resampling.NEAREST).save(prefix + '_overview_grid.png')
    count_rows=[]
    for tag,count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        rgb,hx=bytag[tag]; count_rows.append((tag,hx,rgb,count))
    with open(prefix + '_counts.csv','w',newline='',encoding='utf-8') as f:
        wr=csv.writer(f); wr.writerow(['色号/Tag','HEX','R','G','B','数量/Count'])
        for tag,hx,rgb,count in count_rows: wr.writerow([tag,hx,*rgb,count])

    PW,PH = 1754,1240
    pages=[]
    def new_page():
        p=Image.new('RGB',(PW,PH),'white'); d=ImageDraw.Draw(p)
        rect(d,[35,35,PW-35,PH-35], outline=(30,30,30), width=2)
        return p,d
    # page 1
    p,d = new_page()
    title = 'MARD 221色拼豆图纸' + ('（白底空格版）' if args.empty_white_threshold is not None else '')
    text(d,(70,60),title,f=F['title'])
    bead_text = f'实际用豆：{sum(counts.values())} 颗｜空白格：{empty_count} 格' if args.empty_white_threshold is not None else f'总格数：{w*h} 格'
    meta=[f'尺寸：{w}×{h} 豆', bead_text, f'颜色数量：{len(count_rows)} 色', '色号体系：MARD 221（HEX/RGB近似匹配）']
    for i,m in enumerate(meta): text(d,(75,125+i*31),m,f=F['body'],fill=(45,45,45))
    box1=(70,260,360,550); box2=(390,260,680,550)
    rect(d, box1, width=2); rect(d, box2, width=2)
    text(d,(box1[0],230),'原图',f=F['h2']); text(d,(box2[0],230),'成品预览',f=F['h2'])
    paste_fit(p, orig.convert('RGB'), (box1[0]+10,box1[1]+10,box1[2]-10,box1[3]-10))
    paste_fit(p, preview_big, (box2[0]+10,box2[1]+10,box2[2]-10,box2[3]-10))
    grid_title = f'{w}×{h} 总览网格（无色号，仅看效果）' if args.empty_white_threshold is None else f'{w}×{h} 总览网格（白底为空格，不放豆）'
    text(d,(70,585),grid_title,f=F['h2'])
    paste_fit(p, overview_grid, (70,625,720,1170))
    # legend
    x0,y0=760,105
    text(d,(x0,y0-45),'颜色清单（MARD色号）',f=F['h2'])
    colw=[75,55,115,65]; headers=['色号','色块','HEX','数量']; rowh=27; per_col=36
    for block in range(math.ceil(len(count_rows)/per_col)):
        bx=x0 + block*455
        if bx+sum(colw)>PW-60: break
        y=y0
        for j,hdr in enumerate(headers):
            rect(d,[bx+sum(colw[:j]),y,bx+sum(colw[:j+1]),y+rowh],fill=(238,238,238),outline=(80,80,80))
            text(d,(bx+sum(colw[:j])+colw[j]/2,y+rowh/2),hdr,f=F['small'],anchor='mm')
        y += rowh
        for tag,hx,rgb,count in count_rows[block*per_col:(block+1)*per_col]:
            for j,val in enumerate([tag,'',hx,str(count)]):
                rect(d,[bx+sum(colw[:j]),y,bx+sum(colw[:j+1]),y+rowh],outline=(170,170,170))
                if j==1:
                    d.rectangle([bx+sum(colw[:j])+10,y+5,bx+sum(colw[:j+1])-10,y+rowh-5],fill=rgb,outline=(90,90,90))
                else:
                    text(d,(bx+sum(colw[:j])+colw[j]/2,y+rowh/2),val,f=F['tiny'],anchor='mm')
            y += rowh
    note_box=(1225,990,1680,1170)
    rect(d,note_box,outline=(120,120,120),width=2,fill=(250,250,250))
    notes=['制作提示：','1. 分区图每页约40×40格。','2. 粗线每10格，辅助线每5格。','3. 格内文字为MARD色号。','4. 建议先按分区备豆再拼。']
    if args.empty_white_threshold is not None: notes.insert(1,'1. 白底空格不放豆。')
    for i,n in enumerate(notes[:6]): text(d,(note_box[0]+16,note_box[1]+13+i*25),n,f=F['note'] if i==0 else F['small'])
    pages.append(p)
    # section pages chunks
    chunk=args.chunk
    sec=1
    for sr in range(0,h,chunk):
        for sc in range(0,w,chunk):
            rows=min(chunk,h-sr); cols=min(chunk,w-sc)
            p,d=new_page()
            text(d,(70,58),'MARD拼豆分区图纸',f=F['title'])
            sub=f'第{sec}页｜行 {sr+1}–{sr+rows}｜列 {sc+1}–{sc+cols}｜MARD 221 色号｜尺寸：{w}×{h} 豆'
            text(d,(72,118),sub,f=F['body'],fill=(55,55,55))
            cell=min(25, int(min(1000/max(cols,1), 1000/max(rows,1))))
            grid=make_grid_image(mapped, labels=True, start_r=sr, start_c=sc, rows=rows, cols=cols, cell=cell, number_headers=True)
            p.paste(grid,(245,165))
            qcounts=Counter(); qempty=0
            for yy in range(sr,sr+rows):
                for xx in range(sc,sc+cols):
                    item=mapped[yy][xx]
                    if item is None: qempty += 1
                    else: qcounts[item[0]] += 1
            text(d,(1320,175),'本区用色',f=F['h2'])
            y=218
            if args.empty_white_threshold is not None:
                text(d,(1320,y),f'空白 {qempty}',f=F['small'],fill=(80,80,80)); y += 31
            for tag,count in sorted(qcounts.items(), key=lambda kv: kv[1], reverse=True)[:24]:
                rgb,hx=bytag[tag]
                d.rectangle([1320,y,1350,y+20],fill=rgb,outline=(80,80,80))
                text(d,(1360,y+10),f'{tag}  {count}',f=F['small'],anchor='lm')
                y += 31
            text(d,(72,1188),'提示：打印后可按行列号定位；建议从深色轮廓或大面积色块开始拼。',f=F['small'],fill=(80,80,80))
            pages.append(p); sec += 1
    pdf_path=prefix + '.pdf'
    for i,page in enumerate(pages,1): page.save(f'{prefix}_page{i}.png')
    pages[0].save(pdf_path, save_all=True, append_images=pages[1:], resolution=150.0)
    return pdf_path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--width', type=int, required=True)
    ap.add_argument('--height', type=int)
    ap.add_argument('--out', required=True)
    ap.add_argument('--palette', default='~/.hermes/data/mard221_palette.json')
    ap.add_argument('--chunk', type=int, default=40)
    ap.add_argument('--empty-white-threshold', type=int, default=None)
    args=ap.parse_args()
    pdf=build(args)
    print(pdf)
    print(args.out + '_page1.png')
    print(args.out + '_preview.png')
    print(args.out + '_counts.csv')

if __name__ == '__main__':
    main()
