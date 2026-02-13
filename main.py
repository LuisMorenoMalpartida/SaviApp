import os
import qrcode
from io import BytesIO
from kivy.core.image import Image as CoreImage
from kivy.config import Config
from kivy.uix.modalview import ModalView
from kivy.metrics import dp
from kivy.factory import Factory
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.clock import Clock

# --- CONFIGURACIÓN DE VENTANA ---
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
Config.set('graphics', 'resizable', '0')

from kivymd.tools.hotreload.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
from kivymd.uix.menu import MDDropdownMenu

# --- CLASES PERSONALIZADAS ---

class TarjetaListaJunta(MDCard):
    nombre = StringProperty("")
    monto = StringProperty("")

class TarjetaUnirse(MDCard):
    nombre = StringProperty("")
    monto = StringProperty("")
    organizador = StringProperty("")

class MenuCompartir(ModalView):
    url_invitacion = StringProperty("")
    
    def compartir(self, red_social):
        self.dismiss()
        if red_social == "Copiar Link":
            toast(f"Enlace copiado: {self.url_invitacion}")
        else:
            toast(f"Abriendo {red_social}...")

class TarjetaIntegrante(MDCard):
    """
    Tarjeta visual que representa un CUPO en la junta.
    """
    numero = StringProperty("")
    nombre_alias = StringProperty("Cupo Disponible")
    usuario = StringProperty("Toque para editar") 
    dni = StringProperty("")
    telefono = StringProperty("")
    correo = StringProperty("")
    posicion_numero = StringProperty("left")
    
    # Índice exacto en la lista de cupos
    indice = NumericProperty(0)

    def editar_info(self):
        """Abre el diálogo para editar este cupo específico."""
        app = MDApp.get_running_app()
        pantalla = app.get_manager().get_screen('integrantes_pagos')
        pantalla.mostrar_dialogo_edicion(self.indice)

# --- PANTALLAS ---

class WelcomeScreen(MDScreen): pass
class LoginScreen(MDScreen): pass
class RegisterScreen(MDScreen): pass
class HomeScreen(MDScreen): pass

class ReportarScreen(MDScreen):
    """Pantalla para reportar incumplimientos."""
    def enviar_reporte(self, dni, reclamo):
        if not dni or not reclamo:
            toast("Por favor completa todos los campos")
            return
        
        toast(f"Reporte enviado para DNI: {dni}")
        self.ids.input_dni.text = ""
        self.ids.input_reclamo.text = ""
        # Regresar a la pantalla anterior
        self.manager.current = 'detalles_junta'

class DetallesJuntaScreen(MDScreen):
    nombre_junta = StringProperty("Nombre de la Junta")
    monto_junta = StringProperty("S/ 0.00")

    def ir_a_invitar(self):
        invitar_screen = self.manager.get_screen('invitar')
        codigo = str(hash(self.nombre_junta) % 10000)
        invitar_screen.codigo_junta = f"SAVI-{codigo}"
        self.manager.current = 'invitar'

    def ir_a_info(self):
        info = self.manager.get_screen('info_junta')
        info.monto = self.monto_junta
        self.manager.current = 'info_junta'

    def ir_a_pagos(self):
        pagos = self.manager.get_screen('integrantes_pagos')
        pagos.nombre_junta = self.nombre_junta
        self.manager.current = 'integrantes_pagos'
        
    def ir_a_reportar(self):
        self.manager.current = 'reportar'

class InvitarScreen(MDScreen):
    codigo_junta = StringProperty("SAVI-0000")
    url_invitacion = StringProperty("https://savi.app/unirse")

    def on_enter(self):
        self.generar_qr(self.url_invitacion)

    def generar_qr(self, contenido):
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(contenido)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        texture = CoreImage(buffer, ext='png').texture
        self.ids.img_qr.texture = texture

    def abrir_menu_compartir(self):
        menu = MenuCompartir()
        menu.url_invitacion = self.url_invitacion
        menu.open()
    
    def callback_compartir(self, tipo):
        if tipo == "Copiar Link":
            toast("Enlace copiado al portapapeles")

class InfoJuntaScreen(MDScreen):
    monto = StringProperty("S/ 0.00")
    periodo = StringProperty("Mensual")
    num_personas = StringProperty("1") 
    fecha_inicio = StringProperty("01/03/2026")
    fecha_final = StringProperty("01/01/2027")

    def on_pre_enter(self):
        """Sincronizar el número visual con la lista real al entrar."""
        app = MDApp.get_running_app()
        if app:
            pagos = app.get_manager().get_screen('integrantes_pagos')
            if pagos and pagos.lista_cupos:
                self.num_personas = str(len(pagos.lista_cupos))

    def abrir_dialogo_editar_integrantes(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.textfield import MDTextField
        
        if hasattr(self, 'dialog_integrantes') and self.dialog_integrantes:
            self.dialog_integrantes.dismiss(force=True)
            self.dialog_integrantes = None
        
        app = MDApp.get_running_app()
        pagos = app.get_manager().get_screen('integrantes_pagos')
        cantidad_actual = len(pagos.lista_cupos) if pagos.lista_cupos else 1

        self.text_field_integrantes = MDTextField(
            hint_text="Cantidad de cupos (máx. 10)",
            text=str(cantidad_actual),
            input_filter="int",
            max_text_length=2
        )
        
        def set_integrantes(obj):
            valor = self.text_field_integrantes.text.strip()
            if valor.isdigit():
                n = int(valor)
                if 1 <= n <= 10:
                    self.num_personas = str(n)
                    self.dialog_integrantes.dismiss()
                    pagos.redimensionar_cupos(n)
                    toast(f"Junta actualizada a {n} integrantes")
                else:
                    toast("Mínimo 1, Máximo 10")
            else:
                toast("Número inválido")

        self.dialog_integrantes = MDDialog(
            title="Editar Integrantes",
            type="custom",
            content_cls=self.text_field_integrantes,
            buttons=[
                MDFlatButton(text="CANCELAR", on_release=lambda x: self.dialog_integrantes.dismiss()),
                MDFlatButton(text="GUARDAR", on_release=set_integrantes)
            ]
        )
        self.dialog_integrantes.open()

    def abrir_calendario(self, tipo):
        from kivymd.uix.pickers import MDDatePicker
        
        def on_date_selected(instance, value, date_range):
            fecha_str = value.strftime('%d/%m/%Y')
            if tipo == 'inicio':
                self.fecha_inicio = fecha_str
            else:
                self.fecha_final = fecha_str

        date_picker = MDDatePicker()
        date_picker.bind(on_save=on_date_selected)
        date_picker.open()

class IntegrantesPagosScreen(MDScreen):
    nombre_junta = StringProperty("")
    lista_cupos = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Inicializamos los datos lo antes posible para evitar crashes
        Clock.schedule_once(self.inicializar_datos_default)

    def inicializar_datos_default(self, dt):
        """Crea el cupo de administrador si la lista está vacía."""
        if not self.lista_cupos:
            self.redimensionar_cupos(1)
            self.lista_cupos[0] = {
                'ocupado': True,
                'nombre': 'Tú (Organizador)',
                'usuario': 'Administrador',
                'dni': '', 'telefono': '', 'correo': ''
            }

    def redimensionar_cupos(self, nueva_cantidad):
        """Ajusta el tamaño de la lista conservando los datos existentes."""
        actual = len(self.lista_cupos)
        
        if nueva_cantidad > actual:
            for _ in range(nueva_cantidad - actual):
                self.lista_cupos.append({
                    'ocupado': False,
                    'nombre': 'Cupo Disponible',
                    'usuario': 'Toque para editar',
                    'dni': '', 'telefono': '', 'correo': ''
                })
        elif nueva_cantidad < actual:
            self.lista_cupos = self.lista_cupos[:nueva_cantidad]
        self.renderizar_lista()

    def ocupar_siguiente_cupo_vacio(self, datos_usuario):
        """Busca el primer cupo 'ocupado': False y lo llena."""
        
        # Auto-expandir si está lleno
        todos_llenos = all(c['ocupado'] for c in self.lista_cupos)
        if todos_llenos and len(self.lista_cupos) < 10:
            self.redimensionar_cupos(len(self.lista_cupos) + 1)
            toast("Capacidad aumentada automáticamente")

        for i, cupo in enumerate(self.lista_cupos):
            if not cupo['ocupado']:
                nuevo_cupo = cupo.copy()
                nuevo_cupo.update(datos_usuario)
                nuevo_cupo['ocupado'] = True
                nuevo_cupo['usuario'] = 'Miembro Verificado'
                
                self.lista_cupos[i] = nuevo_cupo
                self.renderizar_lista()
                return True, i + 1 
        
        return False, 0

    def renderizar_lista(self):
        grid = self.ids.get('grid_integrantes', None)
        if not grid: return

        grid.clear_widgets()
        
        for index, datos in enumerate(self.lista_cupos):
            card = TarjetaIntegrante()
            card.numero = str(index + 1)
            card.posicion_numero = "left" if (index + 1) % 2 != 0 else "right"
            
            card.nombre_alias = datos.get('nombre', 'Cupo Disponible')
            card.usuario = datos.get('usuario', 'Toque para editar')
            card.dni = datos.get('dni', '')
            card.telefono = datos.get('telefono', '')
            card.correo = datos.get('correo', '')
            
            card.indice = index
            grid.add_widget(card)

    def mostrar_dialogo_edicion(self, indice, es_registro_qr=False):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.label import MDLabel
        
        datos_actuales = {}
        if not es_registro_qr and indice >= 0:
            if indice < len(self.lista_cupos):
                datos_actuales = self.lista_cupos[indice]
        
        campo_nombre = MDTextField(hint_text="Nombre Completo", text=datos_actuales.get('nombre', ''))
        campo_dni = MDTextField(hint_text="DNI", text=datos_actuales.get('dni', ''), input_filter="int", max_text_length=8)
        campo_telefono = MDTextField(hint_text="Celular", text=datos_actuales.get('telefono', ''), input_filter="int", max_text_length=9)
        campo_correo = MDTextField(hint_text="Correo", text=datos_actuales.get('correo', ''))

        contenido = MDBoxLayout(orientation="vertical", spacing="12dp", adaptive_height=True, size_hint_y=None)
        
        titulo = "¡Únete a la Junta!" if es_registro_qr else "Editar Integrante"
        subtitulo = "Datos del participante"

        contenido.add_widget(MDLabel(text=titulo, font_style="H6", adaptive_height=True))
        contenido.add_widget(MDLabel(text=subtitulo, theme_text_color="Secondary", font_style="Caption"))
        contenido.add_widget(campo_nombre)
        contenido.add_widget(campo_dni)
        contenido.add_widget(campo_telefono)
        contenido.add_widget(campo_correo)

        def guardar(obj):
            if not campo_nombre.text.strip():
                toast("El nombre es obligatorio")
                return
            
            nuevos_datos = {
                'nombre': campo_nombre.text,
                'dni': campo_dni.text,
                'telefono': campo_telefono.text,
                'correo': campo_correo.text,
                'usuario': 'Miembro Manual'
            }

            if es_registro_qr:
                exito, num = self.ocupar_siguiente_cupo_vacio(nuevos_datos)
                if exito:
                    toast(f"¡Bienvenido! Cupo #{num}")
                    MDApp.get_running_app().get_manager().current = 'integrantes_pagos'
                else:
                    toast("¡La junta está llena! (Max 10)")
            else:
                nuevos_datos['ocupado'] = True
                if indice < len(self.lista_cupos):
                    self.lista_cupos[indice].update(nuevos_datos)
                    self.renderizar_lista()
                    toast("Datos guardados")

            self.dialogo.dismiss()

        self.dialogo = MDDialog(
            type="custom",
            content_cls=contenido,
            buttons=[
                MDFlatButton(text="CANCELAR", on_release=lambda x: self.dialogo.dismiss()),
                MDFillRoundFlatButton(text="GUARDAR DATOS", on_release=guardar)
            ],
        )
        self.dialogo.open()

class SaviScreenManager(ScreenManager): pass

class SaviApp(MDApp):
    moneda_seleccionada = StringProperty("Soles")
    menu_periodo = None
    DEBUG = 1
    KV_FILES = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'design.kv')]

    def build_app(self, first=False):
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.material_style = "M3"
        
        if first:
            dir_actual = os.path.dirname(os.path.abspath(__file__))
            ruta_kv = os.path.join(dir_actual, 'design.kv')
            Builder.load_file(ruta_kv)
            
        return SaviScreenManager()

    def set_moneda(self, moneda):
        self.moneda_seleccionada = moneda

    def get_manager(self):
        if hasattr(self, 'root') and self.root:
            if isinstance(self.root, ScreenManager):
                return self.root
            elif hasattr(self.root, 'children'):
                for child in self.root.children:
                    if isinstance(child, ScreenManager):
                        return child
                return self.root.children[0] if self.root.children else self.root
        return self.root

    def abrir_menu_periodo(self, caller):
        """Abre el menú desplegable para el periodo de pago."""
        opciones = ["Mensual", "Quincenal", "Semanal"]
        items = [
            {
                "text": opcion,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=opcion: self.set_periodo(x, caller),
            } for opcion in opciones
        ]
        self.menu_periodo = MDDropdownMenu(
            caller=caller,
            items=items,
            # width_mult eliminado para evitar warning
        )
        self.menu_periodo.open()

    def set_periodo(self, texto, caller):
        caller.text = texto
        self.menu_periodo.dismiss()

    def abrir_picker(self, caller_id):
        from kivymd.uix.pickers import MDDatePicker
        def on_save(instance, value, date_range):
            fecha = value.strftime('%d/%m/%Y')
            screen = self.get_manager().get_screen('home')
            if caller_id == 'inicio':
                screen.ids.txt_fecha_inicio.text = fecha
            else:
                screen.ids.txt_fecha_final.text = fecha
        date_picker = MDDatePicker()
        date_picker.bind(on_save=on_save)
        date_picker.open()

    def crear_junta(self, nombre, monto, cantidad, periodo, inicio, final):
        if not nombre or not monto:
            toast("Nombre y Monto obligatorios")
            return 

        # Validaciones
        cant_int = 1
        if cantidad and cantidad.isdigit():
            cant_int = int(cantidad)
            if cant_int > 10: cant_int = 10
            if cant_int < 1: cant_int = 1
        
        manager = self.get_manager()
        
        # 1. Configurar Pantallas
        info_screen = manager.get_screen('info_junta')
        pagos_screen = manager.get_screen('integrantes_pagos')
        
        info_screen.periodo = periodo
        info_screen.fecha_inicio = inicio if inicio != "Fecha Inicio" else "Pendiente"
        info_screen.fecha_final = final if final != "Fecha Fin" else "Pendiente"
        info_screen.num_personas = str(cant_int)
        
        # Inicializar cupos reales
        pagos_screen.redimensionar_cupos(cant_int)

        # 2. UI Updates en Home
        home_screen = manager.get_screen('home')
        contenedor = home_screen.ids.lista_juntas
        mensaje_guia = home_screen.ids.mensaje_vacio
        mensaje_guia.opacity = 0
        mensaje_guia.height = 0

        simbolo = "S/" if self.moneda_seleccionada == "Soles" else "$"
        monto_final = f"{simbolo} {monto}"
        
        nueva_tarjeta = TarjetaListaJunta(
            nombre=nombre,
            monto=monto_final
        )
        contenedor.add_widget(nueva_tarjeta)

        # Limpiar formulario
        home_screen.ids.input_nombre.text = ""
        home_screen.ids.input_monto.text = ""
        home_screen.ids.input_cantidad.text = ""
        
        home_screen.ids.nav_bottom.switch_tab('tab_mis_juntas')

    def ver_detalles_junta(self, nombre, monto):
        manager = self.get_manager()
        detalles = manager.get_screen('detalles_junta')
        detalles.nombre_junta = nombre
        detalles.monto_junta = monto
        manager.current = 'detalles_junta'

    def procesar_codigo_invitacion(self, codigo):
        if not codigo:
            toast("Ingresa un código válido")
            return
        
        toast(f"Código {codigo} válido. Completar registro...")
        
        try:
            manager = self.get_manager()
            pagos_screen = manager.get_screen('integrantes_pagos')
            
            if not pagos_screen.lista_cupos:
                pagos_screen.inicializar_datos_default(0)
            
            def lanzar_formulario(dt):
                pagos_screen.mostrar_dialogo_edicion(-1, es_registro_qr=True)
            
            Clock.schedule_once(lanzar_formulario, 0.2)
        except Exception as e:
            print(f"Error: {e}")
            toast("Error al procesar.")

if __name__ == '__main__':
    SaviApp().run()