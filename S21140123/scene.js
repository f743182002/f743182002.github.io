/* Space Atlas — dependency-free interactive architectural study.
 * Model proportions trace an unmeasured reference plan. Furniture is illustrative.
 */
(function () {
  'use strict';
  const PI=Math.PI;
  const ROOMS=[
  {
    "id": "balcony1",
    "x": 0,
    "z": 0,
    "w": 8.12,
    "d": 1.72,
    "cx": 4.06,
    "cz": 0.86
  },
  {
    "id": "bedroom1",
    "x": 0,
    "z": 1.72,
    "w": 4.32,
    "d": 4.16,
    "cx": 2.16,
    "cz": 3.8
  },
  {
    "id": "bedroom2",
    "x": 4.32,
    "z": 1.72,
    "w": 3.8,
    "d": 4.16,
    "cx": 6.220000000000001,
    "cz": 3.8
  },
  {
    "id": "kitchen",
    "x": 8.12,
    "z": 0,
    "w": 2.68,
    "d": 5.88,
    "parts": [
      [
        8.12,
        0,
        2.32,
        1.72
      ],
      [
        8.12,
        1.72,
        2.68,
        4.16
      ]
    ],
    "cx": 9.46,
    "cz": 3.8
  },
  {
    "id": "bathroom1",
    "x": 0,
    "z": 5.88,
    "w": 3,
    "d": 2.88,
    "cx": 1.5,
    "cz": 7.32
  },
  {
    "id": "bathroom2",
    "x": 0,
    "z": 8.76,
    "w": 3,
    "d": 1.48,
    "cx": 1.5,
    "cz": 9.5
  },
  {
    "id": "bedroom3",
    "x": 0,
    "z": 8.76,
    "w": 4.32,
    "d": 4.64,
    "parts": [
      [
        3,
        8.76,
        1.32,
        1.48
      ],
      [
        0,
        10.24,
        4.32,
        3.16
      ]
    ],
    "cx": 2.16,
    "cz": 11.8
  },
  {
    "id": "dining",
    "x": 3,
    "z": 5.88,
    "w": 7.8,
    "d": 3.76,
    "parts": [
      [
        3,
        5.88,
        7.8,
        2.88
      ],
      [
        4.32,
        8.76,
        6.48,
        0.88
      ]
    ],
    "cx": 7.6,
    "cz": 7.8
  },
  {
    "id": "living",
    "x": 4.32,
    "z": 9.64,
    "w": 4.92,
    "d": 3.76,
    "cx": 6.78,
    "cz": 11.52
  },
  {
    "id": "stairs",
    "x": 9.24,
    "z": 9.64,
    "w": 1.56,
    "d": 5.28,
    "cx": 10.02,
    "cz": 12.280000000000001
  },
  {
    "id": "balcony2",
    "x": 0,
    "z": 13.4,
    "w": 9.24,
    "d": 1.52,
    "cx": 4.62,
    "cz": 14.16
  }
];
  window.MODEL_ROOMS=ROOMS;
  const NATURAL_PALETTE={wall:'#f7f5ef',edge:'#c6c2b9',floor:'#e5dfd0',wood:'#c7b18e',ground:'#e4e3de',tile:'#e1e1df',fabric:'#d4d4d0',linen:'#f0eeE7',dark:'#686965',accent:'#aecbd8'};
  const COLORS={warm:NATURAL_PALETTE,light:{...NATURAL_PALETTE},dark:{...NATURAL_PALETTE}};

  // The source plan has no survey scale. One illustrative metre = one model
  // unit (consistent with the 1.60 x 2.05 illustrative beds), NOT site dimensions.
  const MODEL_SCALE={unitsPerMeter:1,clearanceMeters:.9,illustrative:true};
  const WALLS=[[0,0,10.44,0],[10.44,0,10.44,1.72],[10.44,1.72,10.8,1.72],[10.8,1.72,10.8,14.92],[10.8,14.92,0,14.92],[0,14.92,0,0],
       [0,1.72,8.12,1.72],[4.32,1.72,4.32,5.88],
       [8.12,0,8.12,.6],[8.12,1.4,8.12,5.88],
       [0,5.88,3.32,5.88],[4.12,5.88,7.08,5.88],[7.88,5.88,8.36,5.88],[9.16,5.88,10.8,5.88],
       [3,5.88,3,7.62],[3,8.42,3,9.36],[3,10.16,3,10.24],
       [0,8.76,3.36,8.76],[4.16,8.76,4.32,8.76],[0,10.24,3,10.24],
       [4.32,8.76,4.32,13.4],[0,13.4,5.6,13.4],[8.32,13.4,9.24,13.4],
       [9.24,9.64,10.8,9.64],[9.24,9.64,9.24,13.84],[9.24,14.64,9.24,14.92]
      ];
  const OPENINGS=[
    {id:'bedroom1-door',name:'房間一門',rooms:['dining','bedroom1'],swing:[4.12,5.88,.8,PI,PI*1.5]},
    {id:'bedroom2-door',name:'房間二門',rooms:['dining','bedroom2'],swing:[7.88,5.88,.8,PI,PI*1.5]},
    {id:'kitchen-door',name:'廚房門',rooms:['dining','kitchen'],swing:[8.36,5.88,.8,0,-PI/2]},
    {id:'bathroom1-door',name:'衛浴一門',rooms:['dining','bathroom1'],swing:[3,8.42,.8,-PI/2,-PI]},
    {id:'bathroom2-door',name:'衛浴二門',rooms:['bedroom3','bathroom2'],swing:[3,10.16,.8,-PI/2,-PI]},
    {id:'bedroom3-door',name:'房間三門',rooms:['dining','bedroom3'],swing:[4.16,8.76,.8,PI,PI/2]},
    {id:'balcony1-door',name:'前陽台門',rooms:['kitchen','balcony1'],swing:[8.12,1.4,.8,-PI/2,-PI]},
    {id:'stairs-door',name:'後陽台與樓梯門',rooms:['balcony2','stairs'],swing:[9.24,14.64,.8,-PI/2,-PI]},
    {id:'balcony2-slider',name:'客廳與後陽台拉門',rooms:['living','balcony2'],kind:'sliding',x1:5.6,z1:13.4,x2:8.32,z2:13.4},
    {id:'living-dining',name:'客餐廳開口',rooms:['living','dining'],kind:'passage',x1:4.32,z1:9.64,x2:9.24,z2:9.64}
  ].map(d=>{if(!d.swing)return d;const [x,z,r,a]=d.swing;return {...d,kind:'swing',x1:x,z1:z,x2:x+Math.cos(a)*r,z2:z+Math.sin(a)*r};});
  const ROOM_OUTLINES={
    bedroom3:[[3,8.76],[4.32,8.76],[4.32,13.4],[0,13.4],[0,10.24],[3,10.24]],
    dining:[[3,5.88],[10.8,5.88],[10.8,9.64],[4.32,9.64],[4.32,8.76],[3,8.76]],
    kitchen:[[8.12,0],[10.44,0],[10.44,1.72],[10.8,1.72],[10.8,5.88],[8.12,5.88]]
  };
  // Bounds are derived from every rendered component, including arms, backs,
  // headboards and counter overhangs. Rendering and audit share these parts.
  const FURNITURE=[];
  function furniture(id,name,room,draw){
    const parts=[];
    const box=(x,y,z,w,h,d,color)=>parts.push({kind:'box',args:[x,y,z,w,h,d,null],color,bounds:[x,z,w,d]});
    const cyl=(x,y,z,r,h,color,n=20,rz=r)=>parts.push({kind:'cylinder',args:[x,y,z,r,h,null,n,rz],color,bounds:[x-r,z-rz,r*2,rz*2]});
    draw(box,cyl);
    const x=Math.min(...parts.map(p=>p.bounds[0])),z=Math.min(...parts.map(p=>p.bounds[1]));
    const w=Math.max(...parts.map(p=>p.bounds[0]+p.bounds[2]))-x,d=Math.max(...parts.map(p=>p.bounds[1]+p.bounds[3]))-z;
    FURNITURE.push({id,name,room,x,z,w,d,parts});
  }
  for(const [id,name,x,z]of[['bedroom1','房間一床',.65,2.35],['bedroom2','房間二床',4.85,2.35],['bedroom3','房間三床',.6,10.7]])furniture(id+'-bed',name,id,(box)=>{
    const w=1.6;box(x,.1,z,w,.22,2.05,'wood');box(x,.32,z,w,.21,2.05,'linen');box(x,.1,z-.06,w,.82,.10,'fabric');box(x+.05,.54,z+.65,w-.1,.035,1.33,'fabric');
    for(let i=0;i<2;i++)box(x+.08+i*w/2,.54,z+.1,w/2-.16,.1,.38,'linen');
  });
  furniture('sofa','淺灰沙發','living',box=>{box(4.65,.15,10.68,.85,.4,1.72,'fabric');box(4.6,.44,10.68,.18,.4,1.72,'fabric');box(4.6,.35,10.6,.93,.3,.12,'fabric');box(4.6,.35,12.36,.93,.3,.12,'fabric');});
  furniture('coffee-table','茶几','living',(box,cyl)=>{cyl(6.6,.07,11.3,.18,.38,'wood');cyl(6.6,.45,11.3,.6,.06,'wood',32,.4);});
  furniture('living-cabinet','客廳矮櫃','living',box=>box(8.65,.1,10.65,.34,.38,1.65,'wood'));
  furniture('dining-table','餐桌','dining',box=>{box(4.65,.74,5.95,2.0,.09,.65,'wood');for(const x of[4.73,6.51])for(const z of[6.03,6.46])box(x,.05,z,.065,.69,.065,'wood');});
  for(const [id,x]of[['south-left',5.15],['south-right',6.15]])furniture('chair-'+id,id==='south-left'?'餐椅南左':'餐椅南右','dining',box=>{
    const z=7.05;box(x-.24,.45,z-.22,.48,.09,.44,'wood');box(x-.24,.5,z+(z<7?-.22:.16),.48,.4,.06,'wood');for(const dx of[-.18,.18])for(const dz of[-.16,.16])box(x+dx,.05,z+dz,.04,.4,.04,'wood');
  });
  furniture('kitchen-counter','廚房櫃體','kitchen',box=>{box(9.95,.05,2.25,.58,.8,2.6,'linen');box(9.91,.85,2.21,.66,.06,2.68,'linen');box(10.03,.915,2.6,.42,.01,.55,'dark');});
  for(const [room,z]of[['bathroom1',6.3],['bathroom2',8.95]]){
    furniture(room+'-toilet',room==='bathroom1'?'衛浴一馬桶':'衛浴二馬桶',room,(box,cyl)=>{cyl(.65,.05,z+.35,.22,.32,'wall',20,.29);box(.44,.07,z+.08,.42,.55,.16,'wall');});
    furniture(room+'-vanity',room==='bathroom1'?'衛浴一洗手台':'衛浴二洗手台',room,box=>{const x=room==='bathroom1'?1.47:1.35;box(x+.03,.1,z,.6,.5,.42,'wood');box(x,.61,z-.03,.66,.06,.48,'linen');});
  }
  Object.assign(window,{MODEL_SCALE,MODEL_WALLS:WALLS,MODEL_OPENINGS:OPENINGS,MODEL_FURNITURE:FURNITURE,MODEL_DOORS:OPENINGS.filter(d=>d.swing).map(d=>d.swing.slice())});

  function rgb(h){if(Array.isArray(h))return h;h=h.replace('#','');return [parseInt(h.slice(0,2),16)/255,parseInt(h.slice(2,4),16)/255,parseInt(h.slice(4,6),16)/255,1];}
  function tint(c,f){c=rgb(c);return [c[0]*f,c[1]*f,c[2]*f,c[3]??1];}
  function mix(a,b,t){a=rgb(a);b=rgb(b);return a.map((v,i)=>i===3?1:v*(1-t)+b[i]*t);}
  const M={
    multiply(a,b){let o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o;},
    perspective(fov,aspect,n,f){let q=1/Math.tan(fov/2);return new Float32Array([q/aspect,0,0,0,0,q,0,0,0,0,(f+n)/(n-f),-1,0,0,2*f*n/(n-f),0]);},
    lookAt(eye,at,up){let z=norm(sub(eye,at)),x=norm(cross(up,z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);},
    point(m,v){let o=[];for(let r=0;r<4;r++)o[r]=m[r]*v[0]+m[4+r]*v[1]+m[8+r]*v[2]+m[12+r]*(v[3]??1);return o;},
    inverse(a){let m=Array.from({length:4},(_,r)=>Array.from({length:8},(_,c)=>c<4?a[c*4+r]:(c-4===r?1:0)));for(let i=0;i<4;i++){let p=i;for(let j=i+1;j<4;j++)if(Math.abs(m[j][i])>Math.abs(m[p][i]))p=j;[m[p],m[i]]=[m[i],m[p]];let f=m[i][i];if(Math.abs(f)<1e-9)return null;for(let k=0;k<8;k++)m[i][k]/=f;for(let j=0;j<4;j++)if(j!==i){f=m[j][i];for(let k=0;k<8;k++)m[j][k]-=f*m[i][k];}}return new Float32Array(Array.from({length:16},(_,i)=>m[i%4][4+Math.floor(i/4)]));}
  };
  function sub(a,b){return a.map((v,i)=>v-b[i]);}function dot(a,b){return a.reduce((s,v,i)=>s+v*b[i],0);}function cross(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}function norm(a){let d=Math.hypot(...a)||1;return a.map(v=>v/d);}
  class Geometry{
    constructor(){this.v=[];this.tris=[];}
    triangle(a,b,c,color,n){color=rgb(color);n=n||norm(cross(sub(b,a),sub(c,a)));for(const p of[a,b,c])this.v.push(...p,...n,...color);this.tris.push({p:[a,b,c],n,c:color});}
    quad(a,b,c,d,color,n){this.triangle(a,b,c,color,n);this.triangle(a,c,d,color,n);}
    box(x,y,z,w,h,d,c){let X=x+w,Y=y+h,Z=z+d;this.quad([x,Y,z],[x,Y,Z],[X,Y,Z],[X,Y,z],c,[0,1,0]);this.quad([x,y,z],[X,y,z],[X,Y,z],[x,Y,z],c,[0,0,-1]);this.quad([x,y,Z],[x,Y,Z],[X,Y,Z],[X,y,Z],c,[0,0,1]);this.quad([x,y,z],[x,Y,z],[x,Y,Z],[x,y,Z],c,[-1,0,0]);this.quad([X,y,z],[X,y,Z],[X,Y,Z],[X,Y,z],c,[1,0,0]);}
    cylinder(x,y,z,r,h,c,n=16,rz=r){for(let i=0;i<n;i++){let a=i*2*PI/n,b=(i+1)*2*PI/n,A=[x+Math.cos(a)*r,y,z+Math.sin(a)*rz],B=[x+Math.cos(b)*r,y,z+Math.sin(b)*rz],C=[B[0],y+h,B[2]],D=[A[0],y+h,A[2]];this.quad(A,B,C,D,c,norm([Math.cos((a+b)/2),0,Math.sin((a+b)/2)]));this.triangle([x,y+h,z],D,C,c,[0,1,0]);}}
    ellipsoid(x,y,z,rx,ry,rz,c){let rings=6,steps=12;for(let j=0;j<rings;j++){let a=-PI/2+j*PI/rings,b=-PI/2+(j+1)*PI/rings;for(let i=0;i<steps;i++){let u=i*2*PI/steps,v=(i+1)*2*PI/steps;let p=(t,s)=>[x+rx*Math.cos(t)*Math.cos(s),y+ry*Math.sin(t),z+rz*Math.cos(t)*Math.sin(s)];this.quad(p(a,u),p(a,v),p(b,v),p(b,u),c);}}}
    line(x1,z1,x2,z2,width,y,c){let dx=x2-x1,dz=z2-z1,l=Math.hypot(dx,dz);if(!l)return;let ox=-dz/l*width/2,oz=dx/l*width/2;this.quad([x1+ox,y,z1+oz],[x2+ox,y,z2+oz],[x2-ox,y,z2-oz],[x1-ox,y,z1-oz],c,[0,1,0]);}
  }
  class SpaceScene{
    constructor(canvas,options={}){
      this.canvas=canvas;this.options=options;this.state={view:'perspective',room:null,furniture:true,walls:'low',theme:'warm',autoRotate:false,zoom:1};this.yaw=-.62;this.pitch=.90;this.targetYaw=this.yaw;this.targetPitch=this.pitch;this.frame=0;this.disposed=false;this.pointers=new Map();this.listeners=[];this.drag=null;
      canvas.style.touchAction='none';canvas.setAttribute('aria-label','可旋轉、縮放及點選空間的互動3D模型');
      this.gl=canvas.getContext('webgl',{antialias:true,alpha:false,preserveDrawingBuffer:true})||canvas.getContext('experimental-webgl',{antialias:true,alpha:false,preserveDrawingBuffer:true});
      if(this.gl)this.initGL();else this.ctx=canvas.getContext('2d');
      this.bind();this.build();this.resize();
      if(typeof ResizeObserver!=='undefined'){this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(canvas);}
    }
    initGL(){
      const gl=this.gl;
      const vs='attribute vec3 aPosition;attribute vec3 aNormal;attribute vec4 aColor;uniform mat4 uMatrix;varying vec3 vNormal;varying vec4 vColor;varying vec3 vPosition;void main(){vNormal=aNormal;vColor=aColor;vPosition=aPosition;gl_Position=uMatrix*vec4(aPosition,1.0);}';
      const fs='precision mediump float;varying vec3 vNormal;varying vec4 vColor;varying vec3 vPosition;uniform vec3 uBackground;void main(){vec3 n=normalize(vNormal);float key=max(0.,dot(n,normalize(vec3(-.6,1.,.55))));float fill=max(0.,dot(n,normalize(vec3(.8,.3,-.6))));float light=.63+.29*key+.10*fill;vec3 col=vColor.rgb*light;gl_FragColor=vec4(col,vColor.a);}';
      const shader=(type,src)=>{let s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
      this.program=gl.createProgram();this.vertShader=shader(gl.VERTEX_SHADER,vs);this.fragShader=shader(gl.FRAGMENT_SHADER,fs);gl.attachShader(this.program,this.vertShader);gl.attachShader(this.program,this.fragShader);gl.linkProgram(this.program);if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(this.program));
      gl.useProgram(this.program);this.buffer=gl.createBuffer();this.glassBuffer=gl.createBuffer();this.loc={p:gl.getAttribLocation(this.program,'aPosition'),n:gl.getAttribLocation(this.program,'aNormal'),c:gl.getAttribLocation(this.program,'aColor'),m:gl.getUniformLocation(this.program,'uMatrix')};gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);
    }
    bind(){
      const on=(name,fn,opts)=>{this.canvas.addEventListener(name,fn,opts);this.listeners.push([name,fn,opts]);};
      on('pointerdown',e=>{if(e.button!==0&&e.pointerType==='mouse')return;this.canvas.focus({preventScroll:true});this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});try{this.canvas.setPointerCapture(e.pointerId);}catch(_){}this.drag={x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,moved:false};if(this.pointers.size===2){this.pinchDistance=this.distance();this.drag.moved=true;}this.canvas.style.cursor='grabbing';});
      on('pointermove',e=>{if(!this.pointers.has(e.pointerId))return;this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});if(this.pointers.size===2){let d=this.distance();if(this.pinchDistance)this.state.zoom=Math.max(.55,Math.min(2.1,this.state.zoom*d/this.pinchDistance));this.pinchDistance=d;if(this.drag)this.drag.moved=true;this.requestRender();return;}if(!this.drag)return;let dx=e.clientX-this.drag.x,dy=e.clientY-this.drag.y;if(Math.hypot(e.clientX-this.drag.startX,e.clientY-this.drag.startY)>5)this.drag.moved=true;if(this.drag.moved){this.yaw-=dx*.008;this.pitch=Math.max(.18,Math.min(1.53,this.pitch+dy*.006));this.state.view='perspective';this.state.autoRotate=false;this.requestRender();}this.drag.x=e.clientX;this.drag.y=e.clientY;});
      const end=e=>{if(!this.pointers.has(e.pointerId))return;let click=this.drag&&!this.drag.moved&&this.pointers.size===1;this.pointers.delete(e.pointerId);this.pinchDistance=null;if(click)this.pick(e.clientX,e.clientY);if(this.pointers.size){const p=this.pointers.values().next().value;this.drag={x:p.x,y:p.y,startX:p.x,startY:p.y,moved:true};}else{this.drag=null;this.canvas.style.cursor='grab';}};
      on('pointerup',end);on('pointercancel',e=>{this.pointers.delete(e.pointerId);this.drag=null;this.pinchDistance=null;this.canvas.style.cursor='grab';});
      on('wheel',e=>{e.preventDefault();this.state.zoom=Math.max(.55,Math.min(2.1,this.state.zoom*Math.exp(-e.deltaY*.001)));this.requestRender();},{passive:false});
      on('dblclick',()=>this.reset());on('contextmenu',e=>e.preventDefault());
      on('keydown',e=>{let acted=true;if(e.key==='ArrowLeft')this.yaw-=.15;else if(e.key==='ArrowRight')this.yaw+=.15;else if(e.key==='ArrowUp')this.pitch=Math.min(1.53,this.pitch+.1);else if(e.key==='ArrowDown')this.pitch=Math.max(.18,this.pitch-.1);else if(e.key==='+'||e.key==='=')this.state.zoom=Math.min(2.1,this.state.zoom+.1);else if(e.key==='-')this.state.zoom=Math.max(.55,this.state.zoom-.1);else if(e.key==='0')this.reset();else acted=false;if(acted){e.preventDefault();this.requestRender();}});
      this.canvas.style.cursor='grab';
    }
    distance(){let p=Array.from(this.pointers.values());return Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);}
    build(){
      const g=this.geometry=new Geometry(),p=COLORS[this.state.theme];this.palette=p;
      const box=(...args)=>g.box(...args),line=(...args)=>g.line(...args);
      box(-30,-.25,-30,70,.02,70,p.ground);
      for(let i=-6;i<23;i++){line(i,-6,i,23,.006,-.225,mix(p.ground,p.edge,.22));line(-6,i,23,i,.006,-.225,mix(p.ground,p.edge,.22));}
      // All coordinates trace source drawing pixels / 25, not real dimensions.
      for(const r of ROOMS){const parts=r.parts||[[r.x,r.z,r.w,r.d]];for(const[x,z,w,d]of parts){
        box(x-.025,-.18,z-.025,w+.05,.18,d+.05,p.edge);
        let tiled=/bathroom|kitchen|balcony|stairs/.test(r.id),c=tiled?p.tile:p.floor;
        box(x,0,z,w,.035,d,c);
        const step=tiled?.58:.22;
        for(let xx=x+step;xx<x+w;xx+=step)line(xx,z,xx,z+d,.008,.038,tint(c,.92));
        if(tiled)for(let zz=z+.58;zz<z+d;zz+=.58)line(x,zz,x+w,zz,.008,.038,tint(c,.92));
      }}
      const h=this.state.walls==='full'?2.5:this.state.walls==='none'?.015:.48;
      const wall=(x1,z1,x2,z2)=>{const t=.10;if(x1===x2){box(x1-t/2,.036,Math.min(z1,z2),t,h,Math.abs(z2-z1),p.wall);box(x1-t/2,h+.036,Math.min(z1,z2),t,.015,Math.abs(z2-z1),p.edge);}else{box(Math.min(x1,x2),.036,z1-t/2,Math.abs(x2-x1),h,t,p.wall);box(Math.min(x1,x2),h+.036,z1-t/2,Math.abs(x2-x1),.015,t,p.edge);}};
      // Exterior boundary, including the stepped outline at upper right.
      WALLS.forEach(s=>wall(...s));
      // Swing arcs: hinge, radius, closed angle, open angle. Source openings only.
      // Open doors are ground symbols only: no upright panel can cross a wall.
      const doorStart=g.tris.length;
      for(const door of OPENINGS.filter(d=>d.kind==='swing')){
        const [cx,cz,r,a,b]=door.swing;
        for(let i=0;i<24;i++){const t=a+(b-a)*i/24,u=a+(b-a)*(i+1)/24;line(cx+Math.cos(t)*r,cz+Math.sin(t)*r,cx+Math.cos(u)*r,cz+Math.sin(u)*r,.022,.06,p.dark);}
        line(cx,cz,cx+Math.cos(b)*r,cz+Math.sin(b)*r,.022,.06,p.dark);
      }
      // Recessed parallel tracks indicate the fully open balcony slider.
      const slider=OPENINGS.find(d=>d.kind==='sliding');
      for(const dz of[-.025,.025])line(slider.x1,slider.z1+dz,slider.x2,slider.z2+dz,.018,.045,p.dark);
      this.doorSymbols=g.tris.slice(doorStart);
      if(this.state.room){
        const room=ROOMS.find(r=>r.id===this.state.room);
        const outline=ROOM_OUTLINES[room.id]||[[room.x,room.z],[room.x+room.w,room.z],[room.x+room.w,room.z+room.d],[room.x,room.z+room.d]];
        outline.forEach(([x,z],i)=>{const [X,Z]=outline[(i+1)%outline.length];line(x,z,X,Z,.065,h+.06,p.accent);});
      }
      if(this.state.furniture)this.furnish(g,p);
      this.opaqueTris=g.tris.filter(t=>t.c[3]>=.999);this.glassTris=g.tris.filter(t=>t.c[3]<.999);
      if(this.gl){const gl=this.gl,data=this.packTriangles(this.opaqueTris);gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);this.count=data.length/10;}this.requestRender();
    }
    furnish(g,p){
      this.renderedFurniture=[];
      for(const item of FURNITURE){
        const start=g.tris.length;
        for(const part of item.parts){const args=part.args.slice();args[part.kind==='box'?6:5]=p[part.color];g[part.kind](...args);}
        this.renderedFurniture.push({id:item.id,triangles:g.tris.slice(start)});
      }
    }
    packTriangles(tris){const data=new Float32Array(tris.length*30);let i=0;for(const t of tris)for(const p of t.p){for(const n of p)data[i++]=n;for(const n of t.n)data[i++]=n;for(const n of t.c)data[i++]=n;}return data;}
    sortedGlass(){return this.glassTris.map(t=>({t,z:t.p.reduce((v,p)=>v+M.point(this.view,p)[2],0)/3})).sort((a,b)=>a.z-b.z).map(q=>q.t);}
    camera(){let a=this.width/this.height,dist=31/this.state.zoom*Math.max(1,.94/a);const target=[5.4,.05,7.46],c=Math.cos(this.pitch);this.eye=[target[0]+Math.sin(this.yaw)*c*dist,target[1]+Math.sin(this.pitch)*dist,target[2]+Math.cos(this.yaw)*c*dist];this.view=M.lookAt(this.eye,target,[0,1,0]);this.matrix=M.multiply(M.perspective(39*PI/180,a,.1,150),this.view);this.inverse=M.inverse(this.matrix);}
    resize(){if(this.disposed)return;let r=this.canvas.getBoundingClientRect();this.width=Math.max(1,r.width||this.canvas.clientWidth||800);this.height=Math.max(1,r.height||this.canvas.clientHeight||600);let dpr=this.gl?Math.min(window.devicePixelRatio||1,2):1;this.canvas.width=Math.round(this.width*dpr);this.canvas.height=Math.round(this.height*dpr);this.requestRender();}
    requestRender(){if(this.disposed||this.frame)return;this.frame=requestAnimationFrame(t=>{this.frame=0;this.render(t);});}
    render(t=0){if(this.disposed)return;if(this.state.autoRotate){if(this.lastTime)this.yaw+=Math.min(t-this.lastTime,50)*.00012;this.lastTime=t;}else this.lastTime=0;this.camera();
      if(this.gl){
        const gl=this.gl,bg=rgb(this.palette.ground);gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.depthMask(true);gl.disable(gl.BLEND);gl.clearColor(bg[0],bg[1],bg[2],1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.program);
        const bind=buffer=>{gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.enableVertexAttribArray(this.loc.p);gl.vertexAttribPointer(this.loc.p,3,gl.FLOAT,false,40,0);gl.enableVertexAttribArray(this.loc.n);gl.vertexAttribPointer(this.loc.n,3,gl.FLOAT,false,40,12);gl.enableVertexAttribArray(this.loc.c);gl.vertexAttribPointer(this.loc.c,4,gl.FLOAT,false,40,24);};
        bind(this.buffer);gl.uniformMatrix4fv(this.loc.m,false,this.matrix);gl.drawArrays(gl.TRIANGLES,0,this.count);
        if(this.glassTris.length){bind(this.glassBuffer);const data=this.packTriangles(this.sortedGlass());gl.bufferData(gl.ARRAY_BUFFER,data,gl.DYNAMIC_DRAW);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.drawArrays(gl.TRIANGLES,0,data.length/10);gl.depthMask(true);gl.disable(gl.BLEND);}
      }else this.renderCanvas();
      if(typeof this.options.onChange==='function')this.options.onChange({...this.state,positions:this.getRoomPositions(),renderer:this.gl?'webgl':'canvas'});if(this.state.autoRotate)this.requestRender();
    }
    renderCanvas(){
      // A small software depth buffer keeps the no-WebGL fallback faithful to
      // the real geometry; painter sorting alone breaks overlapping furniture.
      const ctx=this.ctx;if(!ctx)return;const w=this.canvas.width,h=this.canvas.height;
      if(!this.pixels||this.pixels.width!==w||this.pixels.height!==h){this.pixels=ctx.createImageData(w,h);this.depth=new Float32Array(w*h);}
      const bytes=this.pixels.data,depth=this.depth,light=norm([-.6,1,.55]),fill=norm([.8,.3,-.6]);
      const ambient=.63+.29*light[1]+.10*fill[1],bg=rgb(this.palette.ground).map(v=>Math.round(v*ambient*255));
      depth.fill(Infinity);for(let i=0;i<bytes.length;i+=4){bytes[i]=bg[0];bytes[i+1]=bg[1];bytes[i+2]=bg[2];bytes[i+3]=255;}
      const triangles=[...this.opaqueTris.slice(10),...this.sortedGlass()];
      for(const t of triangles){
        let ps=t.p.map(p=>M.point(this.matrix,p));if(ps.some(p=>p[3]<=.1))continue;
        ps=ps.map(p=>[(p[0]/p[3]+1)*w/2,(1-p[1]/p[3])*h/2,p[2]/p[3]]).sort((a,b)=>a[1]-b[1]);
        const [a,b,c]=ps;if(c[1]-a[1]<.0001)continue;
        let y0=Math.max(0,Math.ceil(a[1]-.5)),y1=Math.min(h-1,Math.floor(c[1]-.5));if(y0>y1)continue;
        const f=.63+.29*Math.max(0,dot(t.n,light))+.10*Math.max(0,dot(t.n,fill));const color=t.c.slice(0,3).map(v=>Math.max(0,Math.min(255,Math.round(v*f*255))));
        for(let y=y0;y<=y1;y++){
          const yy=y+.5,u=(yy-a[1])/(c[1]-a[1]);let xl=a[0]+u*(c[0]-a[0]),zl=a[2]+u*(c[2]-a[2]);
          let q=yy<b[1]?a:b,r=yy<b[1]?b:c;if(r[1]-q[1]<.00001)continue;let v=(yy-q[1])/(r[1]-q[1]),xr=q[0]+v*(r[0]-q[0]),zr=q[2]+v*(r[2]-q[2]);
          if(xl>xr){[xl,xr]=[xr,xl];[zl,zr]=[zr,zl];}const x0=Math.max(0,Math.ceil(xl-.5)),x1=Math.min(w-1,Math.floor(xr-.5));if(x0>x1)continue;
          const dz=(zr-zl)/(xr-xl||1);let z=zl+(x0+.5-xl)*dz,index=y*w+x0;
          for(let x=x0;x<=x1;x++,index++,z+=dz)if(z<=depth[index]){const a=t.c[3],k=index*4;if(a>=.999){depth[index]=z;bytes[k]=color[0];bytes[k+1]=color[1];bytes[k+2]=color[2];}else{bytes[k]=Math.round(color[0]*a+bytes[k]*(1-a));bytes[k+1]=Math.round(color[1]*a+bytes[k+1]*(1-a));bytes[k+2]=Math.round(color[2]*a+bytes[k+2]*(1-a));}}
        }
      }
      ctx.putImageData(this.pixels,0,0);
    }
    pick(cx,cy){if(!this.inverse)return;let r=this.canvas.getBoundingClientRect(),x=(cx-r.left)/r.width*2-1,y=1-(cy-r.top)/r.height*2;let a=M.point(this.inverse,[x,y,-1,1]),b=M.point(this.inverse,[x,y,1,1]);a=a.map(v=>v/a[3]);b=b.map(v=>v/b[3]);let t=(.04-a[1])/(b[1]-a[1]),px=a[0]+t*(b[0]-a[0]),pz=a[2]+t*(b[2]-a[2]);let room=ROOMS.find(r=>(r.parts||[[r.x,r.z,r.w,r.d]]).some(([x,z,w,d])=>px>=x&&px<=x+w&&pz>=z&&pz<=z+d));if(room){this.setRoom(room.id);if(typeof this.options.onSelect==='function')this.options.onSelect(room.id);}}
    getRoomPositions(){let out={};if(!this.matrix)return out;for(const r of ROOMS){let p=M.point(this.matrix,[r.cx,.10,r.cz,1]);let x=(p[0]/p[3]+1)*this.width/2,y=(1-p[1]/p[3])*this.height/2;out[r.id]={x,y,visible:p[3]>0&&x>=0&&x<=this.width&&y>=0&&y<=this.height};}return out;}
    setView(view){if(!['perspective','top','front'].includes(view))return;this.state.view=view;this.state.autoRotate=false;if(view==='top'){this.pitch=PI/2-.002;this.yaw=0;}else if(view==='front'){this.pitch=.25;this.yaw=0;}else{this.pitch=.90;this.yaw=-.62;}this.requestRender();}
    setRoom(id){if(id!==null&&!ROOMS.some(r=>r.id===id))return;this.state.room=id;this.build();}
    setFurniture(value){this.state.furniture=Boolean(value);this.build();}
    setWalls(value){if(!['low','full','none'].includes(value))return;this.state.walls=value;this.build();}
    setTheme(value){if(!COLORS[value])return;this.state.theme=value;this.build();}
    setAutoRotate(value){this.state.autoRotate=Boolean(value);if(value&&this.pitch>1.5){this.pitch=.90;this.state.view='perspective';}this.lastTime=0;this.requestRender();}
    setZoom(value){if(!Number.isFinite(Number(value)))return;this.state.zoom=Math.max(.55,Math.min(2.1,Number(value)));this.requestRender();}
    reset(){this.yaw=-.62;this.pitch=.90;this.state.zoom=1;this.state.view='perspective';this.state.autoRotate=false;this.requestRender();}
    getSnapshot(){this.render(performance.now());return this.canvas.toDataURL('image/png');}
    destroy(){this.disposed=true;cancelAnimationFrame(this.frame);this.observer?.disconnect();this.listeners.forEach(([n,f,o])=>this.canvas.removeEventListener(n,f,o));if(this.gl){this.gl.deleteBuffer(this.buffer);this.gl.deleteBuffer(this.glassBuffer);this.gl.deleteProgram(this.program);this.gl.deleteShader(this.vertShader);this.gl.deleteShader(this.fragShader);}}
  }
  window.SpaceScene=SpaceScene;
})();
