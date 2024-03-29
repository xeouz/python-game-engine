from CursEngine.Curse import Curse

from asyncio import get_event_loop, sleep
import numpy as np
from functools import partial
from gc import collect
from time import perf_counter
from random import randrange

class Matrix:
    def __init__(self,fill:bool=False,border:bool=True,sizex:int=30,sizey:int=10):
        self.x,self.y=sizex,sizey
        self.fill=fill
        self.border=border
        self.entities=[]
        self.refresh()

    def borderize(self,x_ico:int=3,y_ico:int=4) -> None:
        for i in range(self.y):
            self.set(i,0,y_ico)
            self.set(i,-1,y_ico)
        self.matrix[0]=np.array([x_ico]*self.x)
        self.matrix[-1]=np.array([x_ico]*self.x)

        self.matrix[0]=np.array([x_ico]*self.x)
        self.matrix[-1]=np.array([x_ico]*self.x)

    def get(self,x,y) -> int:
        return self.matrix[int(x),int(y)]
    
    def set(self,x,y,value) -> None:
        try:
            self.matrix[int(x),int(y)]=value
        except:
            pass

    def register(self,ent) -> None:
        self.entities.append(ent)

    def unregister(self,ent) -> None:
        return self.entities.pop(self.entities.index(ent))

    def refresh(self) -> None:
        self.matrix=np.array([['11' if not self.fill else '21']*self.x for i in range(self.y)],dtype=str)
        if self.border:
            self.borderize()

    def render_solid_entity(self,ent):
        ent.x+=ent.velocityX
        ent.y+=ent.velocityY
        for i in range(ent.sy):
            for x in range(ent.sx):
                if (ent.y>self.y or ent.y<0 and not ent.destroyed) and ent.ad:
                    ent.destroy()
                if (ent.x>self.x or ent.x<0 and not ent.destroyed) and ent.ad:
                    ent.destroy()

                cx=ent.x+x
                cy=ent.y+i
                
                self.set(cy,cx,'{}{}'.format(2,ent.cpi))

    async def render(self) -> None:
        for ent in self.entities:
            if ent.type=='solid':
                self.render_solid_entity(ent)
            elif ent.type=='ductile':
                for p in ent.body:
                    self.render_solid_entity(p)

class SolidEntity:
    def __init__(self,matrix:Matrix,auto_destruct:bool=True,x:int=0,y:int=0,sizex:int=2,sizey:int=2,shape:str='rect',color_pair_id:int=1):
        self.x,self.y=x,y
        self.shape=shape
        self.type='solid'
        self.sx,self.sy=sizex,sizey
        self.velocityX,self.velocityY=0,0
        self.matrix=matrix
        self.destroyed=False
        self.ad=auto_destruct

        self.cpi=color_pair_id

    def register(self) -> None:
        self.matrix.register(self)

    def destroy(self) -> None:
        self.destroyed=True
        self.matrix.unregister(self)

    def set_velocity(self,x:int=0,y:int=0) -> None:
        self.velocityX,self.velocityY=x,y

    @property
    def corner(self):
        return (self.x+self.sx),(self.y+self.sy)

    def isTouching(self,ent,additive:int=1) -> bool:
        cx,cy=self.corner
        ex,ey=ent.corner
        difx=(cx)-(ex)
        dify=(cy)-(ey)
        difx,dify=abs(difx),abs(dify)
        if ((difx<self.sx) or (difx<ent.sx+ additive)) and ((dify<self.sy) or (dify<ent.sy+ additive)):
            return True
        return False

class DuctileEntity(SolidEntity):
    def __init__(self,matrix:Matrix,auto_destruct:bool=True,x:int=0,y:int=0,head_size:int=2,color_pair_id:int=1):
        self.length=1
        self.body=[self]
        super().__init__(matrix,auto_destruct,x,y,head_size,head_size,'rect',color_pair_id)
        self.type='ductile'

    @property
    def tail(self):
        return self.body[-1] 

    def extend(self,length:int=1,color_pair_id:int=None):
        for i in range(length):
            _,cy=self.tail.corner
            newen=SolidEntity(self.matrix,self.ad,self.tail.x,cy,self.sx,self.sx,'rect',color_pair_id if color_pair_id is not None else self.cpi)
            self.body.append(newen)

    def reduce(self,length:int=1):
        self.body.pop(-1)

class CursEngine:
    def __init__(self,mode:str='inherit',screen_size:tuple=(60,20),framepause:int=0.01, _event_loop_=None, _matrix_:Matrix=None, _curse_base_:Curse=None):
        if _matrix_ is None:
            self.matrix=Matrix(False,True,screen_size[0],screen_size[1])
        else:
            self.matrix=_matrix_
        
        if _event_loop_ is None:
            self.loop=get_event_loop()
        else:
            self.loop=_event_loop_

        if _curse_base_ is None:
            self.curse=Curse(color=True,autostart=False)
        else:
            self.curse=_curse_base_

        self.fp=framepause
        self.entities={}
        self.screen_size=screen_size
        self.mode=mode
        
        if mode=='inherit':
            self.start()


    def start(self):
        self.curse.start()
        self.add_color_pair(0,'white','black')
        self.new_async_task(self.__runner)
        self.loop.run_forever()


    def stop(self):
        self.loop.stop()

    def wrap(self,callbacks:tuple):
        self.before_main=callbacks[0]
        self.main=callbacks[1]
        self.start()

    def randomNumber(self,start:int=0,stop:int=1) -> int:
        try:
            return randrange(start,stop)
        except:
            return start

    def add_color_pair(self,pair_id:int=1,fore:str='red',back:str='black') -> None:
        self.curse.add_color_pair(pair_id=pair_id+1,fore=fore,back=back)

    def new_async_task(self,task_coro_callback=None,params:list=None):
        if task_coro_callback is None:
            return
        if params is not None:
            self.loop.create_task(task_coro_callback(*params))
        else:
            self.loop.create_task(task_coro_callback())

    def get(self,identifier:str='myentity') -> object:
        if identifier in list(self.entities.keys()):
            return self.entities[identifier]
        return None

    def assign(self,identifiers:dict={}) -> None:
        for i in identifiers:
            self.entities[i]=identifiers[i]

    async def new_solid_entity(self, identifier:str='myentity',auto_destruct:bool=True, x:int=0, y:int=0, sizex:int=1, sizey:int=1,shape:str='rect',color_pair_id:int=1):
        en=SolidEntity(self.matrix,auto_destruct=auto_destruct, x=x, y=y, sizex=sizex, sizey=sizey, shape=shape, color_pair_id=color_pair_id+1)
        en.register()
        self.entities[identifier]=en
        return en

    async def new_ductile_entity(self, identifier:str='mydentity',auto_destruct:bool=True,x:int=0,y:int=0, size:int=1, color_pair_id:int=1):
        en=DuctileEntity(self.matrix,auto_destruct=auto_destruct,x=x,y=y,head_size=size,color_pair_id=color_pair_id)
        en.register()
        self.entities[identifier]=en
        return en

    async def new_var(self, identifier:str='myvar', val=None):
        self.entities[identifier]=val

    async def __runner(self):
        if self.mode!='wrap':
            await self.before_main()
        else:
            await self.before_main(self)
        self.curse.start()
        self.curse.screen.idcok(False)
        self.curse.screen.idlok(False)
        t=perf_counter()
        while True:
            delta=perf_counter()-t
            self.curse.erase()
            if self.mode!='wrap':
                r=await self.main()
            else:
                r=await self.main(self)
            self.curse.render_matrix(self.matrix.matrix)
            self.matrix.refresh()
            await self.matrix.render()
            self.curse.refresh()
            collect()
            await sleep(self.fp*delta)
            t=perf_counter()
        
    async def before_main(self) -> None:
        pass

    async def main(self) -> None:
        self.curse.start()
        await sleep(2)
        self.curse.close()



