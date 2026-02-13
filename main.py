import os
import qrcode
from io import BytesIO
from kivy.core.image import Image as CoreImage
from kivy.config import Config
from kivy.uix.modalview import ModalView
from kivy.metrics import dp
from kivy.factory import Factory
from kivy.properties import StringProperty, NumericProperty, ListProperty

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
    Puede estar ocupado o vacio.
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
        # Pasamos el índice de ESTA tarjeta para editar exactamente este cupo
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
        
        # Aquí iría la lógica para enviar a base de datos
        toast(f"Reporte enviado para DNI: {dni}")
        
        # Limpiar campos
        self.ids.input_dni.text = ""
        self.ids.input_reclamo.text = ""
        
        # Volver atrás (opcional)
        # self.manager.current = 'detalles_junta'

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
    num_personas = StringProperty("1") # Este es el valor visual del campo de texto
    fecha_inicio = StringProperty("01/03/2026")
    fecha_final = StringProperty("01/01/2027")

    def abrir_dialogo_editar_integrantes(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.textfield import MDTextField
        
        if hasattr(self, 'dialog_integrantes') and self.dialog_integrantes:
            self.dialog_integrantes.dismiss(force=True)
            self.dialog_integrantes = None
        
        # Recuperamos la cantidad actual real desde la pantalla de pagos
        app = MDApp.get_running_app()
        pagos = app.get_manager().get_screen('integrantes_pagos')
        cantidad_actual = len(pagos.lista_cupos)

        self.text_field_integrantes = MDTextField(
            hint_text="Cantidad de cupos (máx. 20)",
            text=str(cantidad_actual),
            input_filter="int",
            max_text_length=2
        )
        
        def set_integrantes(obj):
            valor = self.text_field_integrantes.text.strip()
            if valor.isdigit():
                n = int(valor)
                if 1 <= n <= 20:
                    self.num_personas = str(n)
                    self.dialog_integrantes.dismiss()
                    # Aquí redimensionamos la lista de cupos (crea vacíos o elimina sobrantes)
                    pagos.redimensionar_cupos(n)
                    toast(f"Junta configurada para {n} personas")
                else:
                    toast("Mínimo 1, Máximo 20")
            else:
                toast("Número inválido")

        self.dialog_integrantes = MDDialog(
            title="Editar Capacidad",
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
    
    # LISTA MAESTRA DE CUPOS
    # Cada elemento es un diccionario:
    # {'ocupado': False, 'nombre': '', 'dni': '', ...}
    lista_cupos = ListProperty([])

    def on_pre_enter(self):
        # Inicialización por defecto si está vacía (creamos 10 cupos por ejemplo, o 1)
        if not self.lista_cupos:
            self.redimensionar_cupos(10) # Valor por defecto de una junta típica
            
            # El cupo 1 siempre es el admin
            self.lista_cupos[0] = {
                'ocupado': True,
                'nombre': 'Tú (Organizador)',
                'usuario': 'Administrador',
                'dni': '', 'telefono': '', 'correo': ''
            }
        
        self.renderizar_lista()

    def redimensionar_cupos(self, nueva_cantidad):
        """Ajusta el tamaño de la lista conservando los datos existentes."""
        actual = len(self.lista_cupos)
        
        if nueva_cantidad > actual:
            # Agregar cupos vacíos
            for _ in range(nueva_cantidad - actual):
                self.lista_cupos.append({
                    'ocupado': False,
                    'nombre': 'Cupo Disponible',
                    'usuario': 'Toque para editar',
                    'dni': '', 'telefono': '', 'correo': ''
                })
        elif nueva_cantidad < actual:
            # Reducir cupos (eliminando desde el final)
            self.lista_cupos = self.lista_cupos[:nueva_cantidad]
            
        self.renderizar_lista()

    def ocupar_siguiente_cupo_vacio(self, datos_usuario):
        """
        Busca el primer cupo 'ocupado': False y lo llena.
        Si no hay cupos, retorna False.
        """
        for i, cupo in enumerate(self.lista_cupos):
            if not cupo['ocupado']:
                # Encontramos un lugar vacío
                nuevo_cupo = cupo.copy()
                nuevo_cupo.update(datos_usuario)
                nuevo_cupo['ocupado'] = True
                nuevo_cupo['usuario'] = 'Miembro Verificado'
                
                # Actualizamos la lista (trigger de Kivy)
                self.lista_cupos[i] = nuevo_cupo
                self.renderizar_lista()
                return True, i + 1 # Retorna éxito y número de integrante
        
        return False, 0 # No hay cupos

    def renderizar_lista(self):
        """Dibuja las tarjetas basadas en lista_cupos."""
        grid = self.ids.get('grid_integrantes', None)
        if not grid: 
            # Intentar buscar de nuevo si Kivy no lo cargó
            for child in self.children:
                if hasattr(child, 'ids') and 'grid_integrantes' in child.ids:
                    grid = child.ids['grid_integrantes']
                    break
        
        if not grid: return

        grid.clear_widgets()
        
        for index, datos in enumerate(self.lista_cupos):
            card = TarjetaIntegrante()
            card.numero = str(index + 1)
            card.posicion_numero = "left" if (index + 1) % 2 != 0 else "right"
            
            # Llenamos visualmente la tarjeta
            card.nombre_alias = datos.get('nombre', 'Cupo Disponible')
            card.usuario = datos.get('usuario', 'Toque para editar')
            card.dni = datos.get('dni', '')
            card.telefono = datos.get('telefono', '')
            card.correo = datos.get('correo', '')
            
            # Importante: Guardamos el índice para saber cuál editar
            card.indice = index
            
            grid.add_widget(card)

    def mostrar_dialogo_edicion(self, indice, es_registro_qr=False):
        """
        Abre dialogo para editar un cupo específico.
        Si es_registro_qr=True, no se edita un índice, sino que se busca cupo vacío.
        """
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.label import MDLabel
        
        # Datos iniciales
        datos_actuales = {}
        if not es_registro_qr and indice >= 0:
            datos_actuales = self.lista_cupos[indice]
        
        # Campos del formulario
        campo_nombre = MDTextField(hint_text="Nombre Completo", text=datos_actuales.get('nombre', ''))
        campo_dni = MDTextField(hint_text="DNI", text=datos_actuales.get('dni', ''), input_filter="int", max_text_length=8)
        campo_telefono = MDTextField(hint_text="Celular", text=datos_actuales.get('telefono', ''), input_filter="int", max_text_length=9)
        campo_correo = MDTextField(hint_text="Correo", text=datos_actuales.get('correo', ''))

        contenido = MDBoxLayout(orientation="vertical", spacing="12dp", adaptive_height=True, size_hint_y=None)
        
        if es_registro_qr:
            titulo = "¡Únete a la Junta!"
            subtitulo = "Tus datos se asignarán al siguiente cupo libre."
        else:
            titulo = "Editar Integrante"
            subtitulo = f"Modificando cupo #{indice + 1}"

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
                # Lógica automática: Buscar primer vacío
                exito, num = self.ocupar_siguiente_cupo_vacio(nuevos_datos)
                if exito:
                    toast(f"¡Bienvenido! Se te asignó el cupo #{num}")
                    MDApp.get_running_app().get_manager().current = 'integrantes_pagos'
                else:
                    toast("¡Lo sentimos! La junta está llena.")
            else:
                # Lógica manual: Editar índice específico
                nuevos_datos['ocupado'] = True # Si lo edito, lo ocupo
                self.lista_cupos[indice].update(nuevos_datos)
                self.renderizar_lista()
                toast("Datos guardados")

            self.dialogo.dismiss()

        self.dialogo = MDDialog(
            title=titulo,
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

    def crear_junta(self, nombre, monto):
        if not nombre or not monto:
            toast("Complete los campos")
            return 

        manager = self.get_manager()
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

        home_screen.ids.input_nombre.text = ""
        home_screen.ids.input_monto.text = ""
        home_screen.ids.nav_bottom.switch_tab('tab_mis_juntas')

    def ver_detalles_junta(self, nombre, monto):
        manager = self.get_manager()
        detalles = manager.get_screen('detalles_junta')
        detalles.nombre_junta = nombre
        detalles.monto_junta = monto
        manager.current = 'detalles_junta'

    def procesar_codigo_invitacion(self, codigo):
        """
        Simula leer el QR. En lugar de agregar a ciegas,
        abre el formulario para llenar datos y busca cupo.
        """
        if not codigo:
            toast("Ingresa un código válido")
            return
        
        toast(f"Código {codigo} válido. Completar registro...")
        
        # Accedemos a la lógica de pagos para usar su formulario
        manager = self.get_manager()
        pagos_screen = manager.get_screen('integrantes_pagos')
        
        # Usamos un pequeño delay para simular carga
        from kivy.clock import Clock
        def lanzar_formulario(dt):
            # True indica que es flujo de QR (buscar cupo libre)
            pagos_screen.mostrar_dialogo_edicion(-1, es_registro_qr=True)
        
        Clock.schedule_once(lanzar_formulario, 0.5)

if __name__ == '__main__':
    SaviApp().run()