#!/usr/bin/env python3
"""Render a continuous, one-shot brand film for Final Exam Prep.skill."""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Compose on the original logical canvas, then downsample for README delivery.
W, H, OUT_W, OUT_H, FPS, SECONDS, SS = 1200, 676, 1024, 577, 18, 16, 2
BG, PAPER, INK, RED, MUTED, LINE = "#F4F1E9", "#FFFEFA", "#191714", "#C43E18", "#817C74", "#CEC7BB"


def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc", size * SS)


def clamp(v): return max(0.0, min(1.0, v))
def expo(v):
    v = clamp(v)
    return 1 if v == 1 else 1 - 2 ** (-10 * v)
def smooth(v):
    v = clamp(v)
    return v * v * (3 - 2 * v)
def spring(v):
    v = clamp(v)
    return 1 - math.exp(-7*v) * math.cos(11*v)
def span(t, a, b, edge=.25): return min(smooth((t-a)/edge), smooth((b-t)/edge))
def bezier(a, b, c, p):
    q = 1-p
    return (q*q*a[0]+2*q*p*b[0]+p*p*c[0], q*q*a[1]+2*q*p*b[1]+p*p*c[1])


def txt(d, xy, s, size, color=INK, bold=False, anchor="mm"):
    d.text((xy[0]*SS, xy[1]*SS), s, font=font(size, bold), fill=color, anchor=anchor)


def line(d, points, fill, width):
    d.line([(x*SS, y*SS) for x, y in points], fill=fill, width=max(1, width*SS), joint="curve")


def tile(d, x, y, label="", scale=1, red=False, alpha=255, angle=0):
    w, h = 124*scale, 70*scale
    layer = Image.new("RGBA", (int((w+20)*SS), int((h+20)*SS)), (0,0,0,0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((10*SS,10*SS,(w+10)*SS,(h+10)*SS), radius=7*SS,
                         fill=RED if red else PAPER, outline=RED if red else LINE, width=2*SS)
    if label:
        ld.text(((w/2+10)*SS,(h/2+10)*SS), label, font=font(max(11,int(17*scale)), True),
                fill=PAPER if red else INK, anchor="mm")
    if angle:
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    layer.putalpha(layer.getchannel("A").point(lambda p: p*alpha//255))
    return layer, (int((x-layer.width/(2*SS))*SS), int((y-layer.height/(2*SS))*SS))


def logo(d, cx, cy, scale=1, reveal=1):
    blocks = [(-31,-31,INK),(3,-31,RED),(-31,3,RED),(3,3,INK)]
    for i,(x,y,c) in enumerate(blocks):
        p = expo((reveal-i*.06)/.76)
        drift = 92*(1-p)
        ang = i*math.pi/2 + reveal*2
        xx, yy = cx+(x+math.cos(ang)*drift)*scale, cy+(y+math.sin(ang)*drift)*scale
        d.rounded_rectangle((xx*SS,yy*SS,(xx+28*scale)*SS,(yy+28*scale)*SS), radius=3*SS, fill=c)
    if reveal > .68:
        p=expo((reveal-.68)/.32)
        pts=[(cx-14*scale,cy+13*scale),(cx-2*scale,cy+25*scale),(cx+30*scale,cy-13*scale)]
        line(d, pts[:2], BG, max(2,int(5*scale)))
        e=(pts[1][0]+(pts[2][0]-pts[1][0])*p,pts[1][1]+(pts[2][1]-pts[1][1])*p)
        line(d,[pts[1],e],BG,max(2,int(5*scale)))


def layout_for(i, phase, t):
    """Distinct motion grammar for each capability chapter."""
    if phase == 0:  # five subject presets: pentagonal orbit
        if i < 5:
            a = -math.pi/2 + i*math.tau/5 + t*.08
            return 600+math.cos(a)*315, 350+math.sin(a)*145, .82, 255, math.sin(a)*3
        a = i*2.399+t*.22
        return 600+math.cos(a)*205, 360+math.sin(a)*105, .44, 85, math.sin(a)*5
    if phase == 1:  # three review frames: weighted triangle
        main = [(600,238),(405,458),(795,458)]
        if 5 <= i <= 7:
            x,y = main[i-5]
            return x, y+math.sin(t*1.8+i)*7, .90, 255, math.sin(t+i)*2
        a=i*2.399+t*.32
        return 600+math.cos(a)*155, 350+math.sin(a)*82, .38, 65, math.sin(a)*6
    if phase == 2:  # four question types: quadrant flip
        main=[(390,250),(810,250),(390,465),(810,465)]
        if 8 <= i <= 11:
            x,y=main[i-8]
            pulse=1+.06*math.sin((t-8.4)*3+i)
            return x,y,.88*pulse,255,math.sin((t-8.4)*2+i)*8
        a=i*2.399-t*.25
        return 600+math.cos(a)*135,355+math.sin(a)*65,.34,55,math.sin(a)*7
    # targeted extraction: left-to-right evidence conveyor, with copy in reserved left field
    lane=i%4
    flow=((t*105+i*137)%520)
    x=540+flow
    y=225+lane*82+math.sin(t*2+i)*5
    return x,y,.54,190 if i%3 else 255,0


def mixed_layout(i, t):
    boundaries=[5.75,8.35,10.72]
    phase=0
    for k,b in enumerate(boundaries):
        if t >= b: phase=k+1
    if phase == 0:
        return layout_for(i,0,t)
    b=boundaries[phase-1]
    mix=smooth((t-b)/.58)
    old=layout_for(i,phase-1,t); new=layout_for(i,phase,t)
    return tuple(old[j]*(1-mix)+new[j]*mix for j in range(5))


def frame_at(t):
    im=Image.new("RGB",(W*SS,H*SS),BG); d=ImageDraw.Draw(im)
    # Persistent camera drift makes every transition part of the same space.
    camx=10*math.sin(t*.42); camy=7*math.sin(t*.31+1)
    txt(d,(88,52),"FINAL EXAM PREP  /  KNOWLEDGE TO ACTION",13,MUTED,False,"lm")
    d.ellipse((62*SS,47*SS,72*SS,57*SS),fill=RED)

    # S1 — a physical exam-range sheet lands, breathes, and is scanned.
    sheet_in=spring(t/1.25); sheet_out=expo((t-3.0)/.75)
    if t < 4.1:
        cx,cy=600+camx,330+camy-230*(1-sheet_in)+420*sheet_out
        ang=-5*(1-sheet_in)+2*math.sin(t*1.7)*(1-sheet_out)
        paper=Image.new("RGBA",(460*SS,320*SS),(0,0,0,0)); p=ImageDraw.Draw(paper)
        p.rounded_rectangle((12*SS,12*SS,448*SS,308*SS),radius=8*SS,fill=PAPER,outline=LINE,width=2*SS)
        p.text((44*SS,55*SS),"期末复习范围",font=font(27,True),fill=INK)
        for i,w in enumerate([300,342,250,325,282]):
            y=(112+i*34)*SS; p.line((44*SS,y,(44+w)*SS,y),fill=LINE,width=3*SS)
        scan=expo((t-1.45)/1.15)
        if t>1.3:
            sy=(92+170*scan)*SS; p.rectangle((32*SS,sy,416*SS,sy+4*SS),fill=RED)
            p.rectangle((32*SS,sy-22*SS,416*SS,sy+22*SS),fill=(196,62,24,18))
        paper=paper.rotate(ang,resample=Image.Resampling.BICUBIC,expand=True)
        im.paste(paper,(int((cx-paper.width/(2*SS))*SS),int((cy-paper.height/(2*SS))*SS)),paper)
        a=span(t,.35,2.8,.4)
        txt(d,(600,570),"先锁定考试范围",28,INK,True)

    # S2/S3 — scan hits pull out of the page and travel on curved paths.
    labels=["文科","理科","工科","语言","竞赛","期末三件套","语言复习","竞赛补缺","论述","计算","语言练习","缺口题"]
    for i,label in enumerate(labels):
        start=2.35+i*.13; p=expo((t-start)/1.05); collapse=expo((t-12.25)/1.0)
        if p<=0 or collapse>=1: continue
        angle=i*2.399
        tx,ty,target_sc,target_alpha,target_angle=mixed_layout(i,t)
        control=(600+math.cos(angle-.85)*260,330+math.sin(angle-.85)*220)
        x,y=bezier((600,330),control,(tx,ty),p)
        x=x*(1-collapse)+600*collapse; y=y*(1-collapse)+330*collapse
        sc=target_sc*spring(p)*(1-.78*collapse)
        alpha=int(target_alpha*(1-collapse))
        layer,pos=tile(d,x+camx,y+camy,label,sc,i in (2,9),alpha,int(target_angle))
        im.paste(layer,pos,layer)
        if .08<p<.96:
            prev=bezier((600,330),control,(tx,ty),max(0,p-.09))
            line(d,[prev,(x,y)],RED if i%4==0 else LINE,2)

    # Central atom grows from the same scan point; no cut.
    if 3.0<t<13.35:
        core=spring((t-3.0)/1.1)*(1-expo((t-12.3)/.85))
        shift=expo((t-10.72)/.7)
        core_x=600+160*shift
        core_y=350
        r=54*core
        d.ellipse(((core_x+camx-r)*SS,(core_y+camy-r)*SS,(core_x+camx+r)*SS,(core_y+camy+r)*SS),fill=INK,outline=RED,width=4*SS)
        txt(d,(core_x+camx,core_y-7+camy),"考点",20,PAPER,True)
        txt(d,(core_x+camx,core_y+20+camy),"驱动",13,"#D9D2C7")
        # rotating evidence ring, visibly connecting process rather than presenting slides
        rr=88+8*math.sin(t*1.6)
        for j in range(4):
            a=t*.7+j*math.pi/2
            x,y=core_x+camx+math.cos(a)*rr,core_y+camy+math.sin(a)*rr
            d.ellipse(((x-5)*SS,(y-5)*SS,(x+5)*SS,(y+5)*SS),fill=RED if j==0 else PAPER,outline=INK)

    # Capability copy rides the camera and changes by rolling, not page replacement.
    copy=[(3.7,6.2,"5 类学科预设", "不同知识结构，调用不同拆解策略"),
          (6.0,8.6,"3 套复习框架", "期末 · 语言 · 竞赛补缺"),
          (8.4,11.0,"4 类题型模板", "论述 · 计算 · 语言练习 · 缺口题"),
          (10.8,12.8,"定向抽取 + 来源追溯", "只取命中页，让每个结果有据可查")]
    for a,b,title,sub in copy:
        q=span(t,a,b,.35)
        if q>0:
            enter=expo((t-a)/.5)
            if a > 10:
                # Reserved copy field: no moving tile passes behind this text.
                x,y=250,255-18*(1-enter)
                txt(d,(x,y),title,34,INK,True,"mm")
                txt(d,(x,y+52),sub,18,RED,False,"mm")
                line(d,[(125,y+92),(375,y+92)],RED,3)
            else:
                y=126-18*(1-enter)
                txt(d,(600,y),title,39,INK,True)
                txt(d,(600,y+50),sub,20,MUTED)

    # S4 BOOM — all moving pieces accelerate inward and the camera punches into the mark.
    boom=expo((t-12.25)/.9)
    if 12.1<t<13.75:
        for j in range(26):
            a=j*2.399; outer=480*(1-boom)+36
            x,y=600+math.cos(a)*outer,330+math.sin(a)*outer*.55
            line(d,[(x,y),(600+math.cos(a)*38,330+math.sin(a)*24)],RED if j%5==0 else LINE,max(1,int(3*(1-boom))))
        if .42<boom<.82:
            flash=int(68*math.sin((boom-.42)/.4*math.pi))
            overlay=Image.new("RGBA",im.size,(255,254,250,flash)); im=Image.alpha_composite(im.convert("RGBA"),overlay).convert("RGB"); d=ImageDraw.Draw(im)

    # S5 — the exact same tiles settle into the logo, then hold decisively.
    if t>12.75:
        reveal=spring((t-12.75)/1.0)
        scale=1.25+.2*math.exp(-3*(t-12.75))*math.sin(12*(t-12.75))
        logo(d,600,248,scale,reveal)
        name=expo((t-13.25)/.7)
        if name>0:
            txt(d,(600,374+24*(1-name)),"Final Exam Prep.skill",54,INK,True)
            txt(d,(600,442),"把考试范围，编译成复习行动",27,RED)
            w=420*expo((t-13.6)/.7); line(d,[(600-w/2,500),(600+w/2,500)],RED,4)
            txt(d,(600,535),"5 类学科 · 3 套框架 · 4 类题型 · 质量门禁",18,MUTED,True)

    txt(d,(1150,640),"CREATED BY HUASHU-DESIGN",10,"#A7A198",False,"rs")
    return im.resize((OUT_W,OUT_H),Image.Resampling.LANCZOS)


def main():
    out=Path(__file__).resolve().parent.parent/"assets"/"hero.gif"
    frames=[
        frame_at(i/FPS).quantize(colors=96, method=Image.Quantize.MEDIANCUT)
        for i in range(FPS*SECONDS)
    ]
    frames[0].save(out,save_all=True,append_images=frames[1:],duration=round(1000/FPS),loop=0,optimize=True,disposal=2)
    print(out)
    return 0


if __name__=="__main__": raise SystemExit(main())
