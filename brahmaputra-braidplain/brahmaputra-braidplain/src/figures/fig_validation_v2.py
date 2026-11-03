import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

man = {"CW":[1.32,2.05,2.98,2.29,1.89,3.14,3.30,2.18],
       "BBW":[3.06,6.21,3.37,5.76,4.20,5.29,5.74,2.71],
       "VBW":[1.65,1.47,2.97,2.09,4.60,5.66,1.99,4.52],
       "thr":[3,6,8,7,4,8,5,3], "units":[3,7,6,8,5,8,6,4]}
shp=["CS_07","CS_03","CS_01","CS_04","CS_05","CS_06","CS_08","CS_02"]
idx=[shp.index(f"CS_0{i}") for i in range(1,9)]
ro=lambda d:{k:[v[i] for i in idx] for k,v in d.items()}
attn9=ro({"CW":[3.66,3.37,1.46,2.41,2.06,3.51,2.41,2.13],"BBW":[4.22,4.78,3.92,6.41,5.58,6.36,2.61,6.73],
          "VBW":[2.06,2.16,1.85,0.96,2.86,3.82,4.17,1.43],"thr":[8,5,2,4,4,7,2,7],"units":[10,9,4,8,8,12,9,9]})
seg9=ro({"CW":[3.56,3.50,1.46,2.23,2.26,4.19,2.40,2.15],"BBW":[5.17,5.21,4.03,6.84,5.68,6.73,2.74,6.95],
         "VBW":[1.21,1.60,1.74,0.71,2.56,2.77,4.05,1.19],"thr":[7,6,2,4,5,11,2,7],"units":[8,7,4,7,7,14,5,10]})
attn6=ro({"CW":[3.42,3.19,1.40,2.20,1.89,3.03,2.24,2.28],"BBW":[3.42,3.12,3.20,5.79,3.56,4.11,1.98,5.79],
          "VBW":[3.10,4.00,2.63,1.79,5.05,6.55,4.97,2.22],"thr":[6,4,2,3,4,7,2,8],"units":[10,11,4,9,5,11,5,10]})

models=[("Attention U-Net, 9 bands",attn9,"#2a78d6"),
        ("SegFormer-B2, 9 bands",seg9,"#eb6834"),
        ("Attention U-Net, 6 bands",attn6,"#1baf7a")]
labels={"CW":"Channel width","BBW":"Bare bar width","VBW":"Vegetated bar width",
        "thr":"Thread count","units":"Bar unit count"}

def r2(k,d): return stats.pearsonr(man[k],d[k])[0]**2
def bias(k,d): return float(np.mean(np.array(d[k])-np.array(man[k])))

INK="#222222"; MUTED="#666666"; GRID="#e4e4e4"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.edgecolor":MUTED,
                     "axes.labelcolor":INK,"xtick.color":MUTED,"ytick.color":INK})

fig,axes=plt.subplots(1,3,figsize=(13,4.6),
                      gridspec_kw={"width_ratios":[1.25,1,1],"wspace":0.08})
bh=0.26

def hbars(ax,keys,fn,fmt,xlim,xlabel,title,zero=False):
    y=np.arange(len(keys))[::-1]
    for j,(name,d,col) in enumerate(models):
        vals=[fn(k,d) for k in keys]
        pos=y+(1-j)*bh
        ax.barh(pos,vals,height=bh-0.03,color=col,edgecolor="white",linewidth=0.6,zorder=3)
        for p,v in zip(pos,vals):
            off=0.012*(xlim[1]-xlim[0])
            ha="left" if v>=0 else "right"
            ax.text(v+(off if v>=0 else -off),p,fmt(v),va="center",ha=ha,fontsize=7.5,color=INK,zorder=4)
    ax.set_yticks(y); ax.set_yticklabels([labels[k] for k in keys])
    ax.set_xlim(*xlim); ax.set_xlabel(xlabel)
    ax.set_title(title,loc="left",fontsize=10,color=INK)
    ax.grid(axis="x",color=GRID,lw=0.7,zorder=0)
    if zero: ax.axvline(0,color=MUTED,lw=0.9,zorder=2)
    for s in ("top","right","left"): ax.spines[s].set_visible(False)
    ax.tick_params(axis="y",length=0)

allk=["CW","BBW","VBW","thr","units"]
hbars(axes[0],allk,r2,lambda v:f"{v:.2f}",(0,1.12),"R² (higher is better)",
      "(a) Agreement with manual measurement")
hbars(axes[1],["CW","BBW","VBW"],bias,lambda v:f"{v:+.2f}",(-1.6,1.4),
      "Mean bias, km (model − manual)","(b) Width bias",zero=True)
hbars(axes[2],["thr","units"],bias,lambda v:f"{v:+.2f}",(-1.6,3.4),
      "Mean bias, count (model − manual)","(c) Count bias",zero=True)
for ax in axes[1:]:
    ax.yaxis.tick_right(); ax.tick_params(axis="y",pad=2)
axes[1].set_yticklabels(axes[1].get_yticklabels());
# keep labels on right for b and c so they sit next to their own bars
fig.subplots_adjust(left=0.13,right=0.88,bottom=0.26,top=0.9,wspace=0.55)

h=[plt.Rectangle((0,0),1,1,color=c) for _,_,c in models]
fig.legend(h,[n for n,_,_ in models],loc="lower center",ncol=3,frameon=False,
           bbox_to_anchor=(0.5,0.0),fontsize=9)
fig.savefig("/mnt/user-data/outputs/fig_geometric_validation.png",dpi=300,bbox_inches="tight")
fig.savefig("/mnt/user-data/outputs/fig_geometric_validation.pdf",bbox_inches="tight")
from PIL import Image
Image.open("/mnt/user-data/outputs/fig_geometric_validation.png").convert("RGB").save(
    "/mnt/user-data/outputs/fig_geometric_validation.jpg","JPEG",quality=95,dpi=(300,300))
print("ok")
