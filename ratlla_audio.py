"""Lazy optional audio, with bounded voice count and one-shot event cooldowns."""
import os,time
class Audio:
    def __init__(self, pg):
        self.pg=pg;self.sounds={};self.ready=False;self.attempted=False;self.last={};self.last_any=-100;self.channel=None
    def unlock(self):
        if self.ready or self.attempted:return
        self.attempted=True
        try:
            if not self.pg.mixer.get_init():self.pg.mixer.init()
            self.channel=self.pg.mixer.Channel(0);self.ready=True
        except Exception:self.ready=False
    def play(self,name,prefs):
        if not self.ready or not prefs.get('sound',True) or not prefs.get('volume',60):return
        now=time.monotonic()
        if now-self.last.get(name,-100)<.14 or now-self.last_any<.055:return
        try:
            if name not in self.sounds:self.sounds[name]=self.pg.mixer.Sound(os.path.join(os.path.dirname(__file__),'assets','sounds',name+'.wav'))
            if self.channel.get_busy() and name not in ('win','result','achievement','purchase'):return
            sound=self.sounds[name];sound.set_volume(.45*prefs.get('volume',60)/100);self.channel.play(sound);self.last[name]=now;self.last_any=now
        except Exception:pass
