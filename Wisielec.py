
import os
import random
import json
import csv
import tkinter as tk
from tkinter import messagebox, simpledialog
from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey
)
from sqlalchemy.orm import (
    declarative_base, relationship, sessionmaker
)
from cryptography.fernet import Fernet







Base = declarative_base()

class Gracz(Base):
    __tablename__ = 'gracze'
    id = Column(Integer, primary_key=True)
    nazwa = Column(String, unique=True)
    haslo = Column(String)
    wyniki = relationship('Wynik', back_populates='gracz')

class Kategoria(Base):
    __tablename__ = 'kategorie'
    id = Column(Integer, primary_key=True)
    nazwa = Column(String, unique=True)
    hasla = relationship('Haslo', back_populates='kategoria')

class Haslo(Base):
    __tablename__ = 'hasla'
    id = Column(Integer, primary_key=True)
    tekst = Column(String)
    kategoria_id = Column(Integer, ForeignKey('kategorie.id'))
    kategoria = relationship('Kategoria', back_populates='hasla')

class Wynik(Base):
    __tablename__ = 'wyniki'
    id = Column(Integer, primary_key=True)
    gracz_id = Column(Integer, ForeignKey('gracze.id'))
    gracz = relationship('Gracz', back_populates='wyniki')
    tryb = Column(String)
    czy_wygrana = Column(Integer)







class MenadzerBazy:
    def __init__(self, sciezka='wisielec.db'):
        self.engine = create_engine(f'sqlite:///{sciezka}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._seed()

    def _seed(self):
        sesja = self.Session()
        if sesja.query(Kategoria).count() == 0:
            kat = Kategoria(nazwa='podstawowa')
            slowa = ['python','komputer','programowanie','biblioteka','javascript']
            kat.hasla = [Haslo(tekst=sl.upper()) for sl in slowa]
            sesja.add(kat)
            sesja.commit()
        sesja.close()








class MenadzerAutoryzacji:
    def __init__(self, mb: MenadzerBazy):
        self.mb = mb
        keyfile = 'klucz.key'
        if not os.path.exists(keyfile):
            open(keyfile,'wb').write(Fernet.generate_key())
        self.f = Fernet(open(keyfile,'rb').read())

    def rejestruj(self, nazwa, haslo):
        sesja = self.mb.Session()
        zaszyf = self.f.encrypt(haslo.encode()).decode()
        g = Gracz(nazwa=nazwa, haslo=zaszyf)
        sesja.add(g); sesja.commit(); sesja.close()

    def zaloguj(self, nazwa, haslo):
        sesja = self.mb.Session()
        g = sesja.query(Gracz).filter_by(nazwa=nazwa).first()
        sesja.close()
        if g and self.f.decrypt(g.haslo.encode()).decode() == haslo:
            return g
        return None








class MenadzerGry:
    def __init__(self, sesja, tryb):
        self.sesja = sesja
        self.tryb = tryb
        self.slowo = ''
        self.zgadniete = set()
        self.bledne = 0
        self.max_bledne = 6

    def wybierz_haslo(self, nazwa_kategorii=None):
        q = self.sesja.query(Haslo)
        if nazwa_kategorii:
            q = q.join(Kategoria).filter(Kategoria.nazwa==nazwa_kategorii)
        lista = q.all()
        if lista:
            self.slowo = random.choice(lista).tekst.upper()

    def zgadnij(self, litera):
        lit = litera.upper()
        if lit not in self.zgadniete:
            self.zgadniete.add(lit)
            if lit not in self.slowo:
                self.bledne += 1
        pokaz = ' '.join(c if c in self.zgadniete else '_' for c in self.slowo)
        przegrana = self.bledne >= self.max_bledne
        wygrana = all(c in self.zgadniete for c in self.slowo)
        return pokaz, przegrana, wygrana








class MenadzerStatystyk:
    def __init__(self, sesja, gracz):
        self.sesja = sesja
        self.gracz = gracz

    def pobierz(self):
        return self.sesja.query(Wynik).filter_by(gracz_id=self.gracz.id).all()







class MenadzerEksportu:
    def __init__(self, sesja, gracz):
        self.sesja = sesja
        self.gracz = gracz

    def do_csv(self, plik='wyniki.csv'):
        wyn = self.sesja.query(Wynik).filter_by(gracz_id=self.gracz.id).all()
        with open(plik,'w',newline='') as f:
            w = csv.writer(f)
            w.writerow(['tryb','wygrana'])
            for r in wyn:
                w.writerow([r.tryb, r.czy_wygrana])
        return plik

    def do_json(self, plik='wyniki.json'):
        wyn = self.sesja.query(Wynik).filter_by(gracz_id=self.gracz.id).all()
        dane = [{'tryb':r.tryb,'wygrana':r.czy_wygrana} for r in wyn]
        with open(plik,'w') as f:
            json.dump(dane,f)
        return plik









class MenadzerUstawien:
    def __init__(self, plik='ustawienia.json'):
        self.plik = plik
        if os.path.exists(plik):
            self.data = json.load(open(plik))
        else:
            self.data = {'trudnosc':'srednia'}

    def zapisz(self):
        json.dump(self.data, open(self.plik,'w'))








class Aplikacja(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('wisielec')
        self.mb = MenadzerBazy()
        self.ma = MenadzerAutoryzacji(self.mb)
        self.sesja = self.mb.Session()
        self.gracz = self._ekran_logowania()
        if self.gracz:
            self.ust = MenadzerUstawien()
            self._ekran_menu()
            self.mainloop()

    def _ekran_logowania(self):
        akcja = messagebox.askquestion('logowanie','masz konto')
        if akcja=='yes':
            naz = simpledialog.askstring('logowanie','nazwa')
            pas = simpledialog.askstring('logowanie','haslo',show='*')
            g = self.ma.zaloguj(naz,pas)
            if g: return g
        else:
            naz = simpledialog.askstring('rejestracja','nowa nazwa')
            pas = simpledialog.askstring('rejestracja','haslo',show='*')
            self.ma.rejestruj(naz,pas)
            return self._ekran_logowania()
        return None

    def _czysc(self):
        for w in self.winfo_children():
            w.destroy()

    def _ekran_menu(self):
        self._czysc()
        tk.Button(self, text='solo', command=lambda: self._ekran_gry('solo')).pack(fill='x')
        tk.Button(self, text='duo', command=lambda: self._ekran_gry('duo')).pack(fill='x')
        tk.Button(self, text='statystyki', command=self._ekran_stat).pack(fill='x')
        tk.Button(self, text='export', command=self._ekran_export).pack(fill='x')
        tk.Button(self, text='ustawienia', command=self._ekran_ust).pack(fill='x')
        tk.Button(self, text='wyjdz', command=self.destroy).pack(fill='x')

    def _ekran_gry(self, tryb):
        self._czysc()
        self.gm = MenadzerGry(self.sesja, tryb)
        self.gm.wybierz_haslo()
        self.kanwa = tk.Canvas(self, width=200, height=250)
        self.kanwa.pack()
        self.slowo_var = tk.StringVar(); tk.Label(self, textvariable=self.slowo_var,font=(None,18)).pack()
        frame = tk.Frame(self); frame.pack()
        tk.Label(frame, text='litera').pack(side='left')
        self.entry = tk.Entry(frame, width=5); self.entry.pack(side='left')
        self.btn = tk.Button(self, text='zgadnij', command=self._guess); self.btn.pack()
        self.status_var = tk.StringVar(); tk.Label(self, textvariable=self.status_var).pack()
        tk.Button(self, text='menu', command=self._ekran_menu).pack(fill='x')
        self._draw(); self._update()

    def _draw(self):
        b = self.gm.bledne
        self.kanwa.delete('all')
        self.kanwa.create_line(20,230,180,230)
        self.kanwa.create_line(50,230,50,20)
        self.kanwa.create_line(50,20,130,20)
        self.kanwa.create_line(130,20,130,40)
        if b>0: self.kanwa.create_oval(110,40,150,80)
        if b>1: self.kanwa.create_line(130,80,130,140)
        if b>2: self.kanwa.create_line(130,100,100,120)
        if b>3: self.kanwa.create_line(130,100,160,120)
        if b>4: self.kanwa.create_line(130,140,100,180)
        if b>5: self.kanwa.create_line(130,140,160,180)

    def _update(self):
        pok, przegr, wygr = self.gm.zgadnij('')
        self.slowo_var.set(pok)

    def _guess(self):
        lit = self.entry.get().upper()
        self.entry.delete(0,'end')
        if not lit.isalpha() or len(lit)!=1:
            self.status_var.set('wpisz jeden znak'); return
        pok, przegr, wygr = self.gm.zgadnij(lit)
        self._draw(); self.slowo_var.set(pok)
        if przegr or wygr:
            wynik = 1 if wygr else 0
            nr = Wynik(gracz_id=self.gracz.id, tryb=self.gm.tryb, czy_wygrana=wynik)
            ses = self.sesja; ses.add(nr); ses.commit()
            msg = 'wygrales' if wygr else f'przegrales haslo {self.gm.slowo}'
            messagebox.showinfo('koniec', msg)
            self.btn.config(state='disabled')

    def _ekran_stat(self):
        self._czysc()
        mgr = MenadzerStatystyk(self.sesja, self.gracz)
        wyn = mgr.pobierz()
        txt = '\n'.join(f'{w.tryb}: {"win" if w.czy_wygrana else "loss"}' for w in wyn) or 'brak'
        tk.Label(self, text=txt).pack()
        tk.Button(self, text='menu', command=self._ekran_menu).pack(fill='x')

    def _ekran_export(self):
        mgr = MenadzerEksportu(self.sesja, self.gracz)
        csvf = mgr.do_csv(); jsonf = mgr.do_json()
        messagebox.showinfo('export', f'zapisano {csvf} i {jsonf}')
    
    def _ekran_ust(self):
        self._czysc()
        lvl = simpledialog.askstring('ustawienia','trudnosc (latwa/srednia/trudna)')
        if lvl: self.ust.data['trudnosc'] = lvl; self.ust.zapisz()
        tk.Label(self, text=f'trudnosc {self.ust.data["trudnosc"]}').pack()
        tk.Button(self, text='menu', command=self._ekran_menu).pack(fill='x')

if __name__ == '__main__':
    Aplikacja()
