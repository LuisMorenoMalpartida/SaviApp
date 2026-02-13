import os
import qrcode # <--- NUEVO: Para generar el QR
from io import BytesIO # <--- NUEVO: Para manejar la imagen en memoria
from kivy.core.image import Image as CoreImage # <--- NUEVO
from kivy.config import Config
from kivy.uix.modalview import ModalView # <--- NUEVO
from kivy.metrics import dp # <--- NUEVO
from kivy.core.text import LabelBase # <--- NUEVO
from kivy.factory import Factory

# --- 1. CONFIGURACIÓN DE VENTANA ---
# Simulamos un entorno móvil para que el diseño se vea correctamente en PC
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
Config.set('graphics', 'resizable', '0')

# from kivymd.app import MDApp # <--- COMENTADO: Usamos HotReload en su lugar
from kivymd.tools.hotreload.app import MDApp # <--- NUEVO: Para Hot Reload
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.bottomsheet import MDCustomBottomSheet # <--- CORREGIDO: Usamos Custom en lugar de Grid
from kivymd.uix.boxlayout import MDBoxLayout # <--- NUEVO
from kivymd.uix.gridlayout import MDGridLayout # <--- NUEVO
from kivymd.uix.button import MDIconButton # <--- NUEVO
from kivymd.uix.label import MDLabel # <--- NUEVO
from kivymd.toast import toast # <--- NUEVO: Para mensajes flotantes
from kivy.properties import StringProperty, NumericProperty, ObjectProperty

# --- 2. CLASES DE COMPONENTES PERSONALIZADOS ---
# Estas clases deben existir en Python para que el archivo KV pueda usarlas

class TarjetaListaJunta(MDCard):
    """Representa cada junta creada en la lista de 'Mis Juntas'."""
    nombre = StringProperty("")
    monto = StringProperty("")

class TarjetaUnirse(MDCard):
    """Representa las juntas disponibles en la pestaña 'Unirse'."""
    nombre = StringProperty("")
    monto = StringProperty("")
    organizador = StringProperty("")

class MenuCompartir(ModalView):
    """Menú modal para compartir (definido en KV)."""
    url_invitacion = StringProperty("")
    
    def compartir(self, red_social):
        """Acción al seleccionar una app."""
        self.dismiss()
        if red_social == "Copiar Link":
            # Aquí iría la lógica para copiar al portapapeles
            toast(f"Enlace copiado: {self.url_invitacion}")
        else:
            # En un móvil real, aquí usarías 'Intent' para abrir la app
            toast(f"Abriendo {red_social}...")

class InvitarScreen(MDScreen):
    """Pantalla específica para compartir el código y QR."""
    codigo_junta = StringProperty("SAVI-8823") # Código de ejemplo
    url_invitacion = StringProperty("https://savi.app/j/8823")

    def on_enter(self):
        """Se ejecuta al entrar a la pantalla: Genera el QR automáticamente."""
        self.generar_qr(self.url_invitacion)

    def generar_qr(self, contenido):
        """Genera un código QR y lo asigna al widget de imagen."""
        # Crear el objeto QR
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(contenido)
        qr.make(fit=True)
        
        # Crear imagen en memoria (para no guardar archivos)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Convertir a textura de Kivy y asignarla a la imagen en el KV
        texture = CoreImage(buffer, ext='png').texture
        self.ids.img_qr.texture = texture

    def abrir_menu_compartir(self):
        """Abre el menú modal definido en KV."""
        menu = MenuCompartir()
        menu.url_invitacion = self.url_invitacion
        menu.open()

# --- 3. DEFINICIÓN DE PANTALLAS ---

class WelcomeScreen(MDScreen):
    """Pantalla inicial con el carrusel de 3 imágenes."""
    pass

class LoginScreen(MDScreen):
    """Pantalla de inicio de sesión."""
    pass

class RegisterScreen(MDScreen):
    """Pantalla de registro de nuevos usuarios."""
    pass

class HomeScreen(MDScreen):
    """Contenedor principal con las 5 secciones de navegación inferior."""
    pass

class DetallesJuntaScreen(MDScreen):
    """Pantalla de gestión interna (Detalles, Invitar, Pagos, Reportar)."""
    nombre_junta = StringProperty("Nombre de la Junta")
    monto_junta = StringProperty("S/ 0.00")

    def ir_a_invitar(self):
        """Navega a la pantalla de invitación."""
        invitar_screen = self.manager.get_screen('invitar')
        invitar_screen.codigo_junta = "SAVI-" + str(hash(self.nombre_junta) % 10000) # Generar código pseudo-aleatorio
        self.manager.current = 'invitar'

    def ir_a_info(self):
        """Navega a la pantalla de información detallada."""
        info = self.manager.get_screen('info_junta')
        info.monto = self.monto_junta
        self.manager.current = 'info_junta'

    def ir_a_pagos(self):
        """Navega a la pantalla de integrantes y pagos."""
        pagos = self.manager.get_screen('integrantes_pagos')
        pagos.nombre_junta = self.nombre_junta
        self.manager.current = 'integrantes_pagos'

class InfoJuntaScreen(MDScreen):
    """Pantalla con la información detallada de la junta (Periodo, Personas, Sorteo, etc.)."""
    monto = StringProperty("S/ 0.00")
    periodo = StringProperty("Mensual") # Ejemplo
    num_personas = StringProperty("1") # Por defecto 1
    fecha_inicio = StringProperty("01/03/2026")
    fecha_final = StringProperty("01/01/2027")

    def abrir_dialogo_editar_integrantes(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.textfield import MDTextField
        
        if hasattr(self, 'dialog_integrantes') and self.dialog_integrantes:
            self.dialog_integrantes.dismiss(force=True)
            self.dialog_integrantes = None
        
        self.text_field_integrantes = MDTextField(
            hint_text="Cantidad de integrantes (máx. 10)",
            text=self.num_personas,
            input_filter="int",
            max_text_length=2
        )
        
        def set_integrantes(obj, *args):
            valor = self.text_field_integrantes.text.strip()
            if valor.isdigit():
                n = int(valor)
                if 1 <= n <= 10:
                    self.num_personas = str(n)
                    self.dialog_integrantes.dismiss()
                    # Sincronizar con IntegrantesPagosScreen
                    manager = self.manager if hasattr(self, 'manager') else self.parent.manager
                    pagos = manager.get_screen('integrantes_pagos')
                    pagos.actualizar_integrantes(n)
                else:
                    from kivymd.toast import toast
                    toast("El máximo es 10 y mínimo 1")
            else:
                from kivymd.toast import toast
                toast("Ingrese un número válido")

        self.dialog_integrantes = MDDialog(
            title="Editar número de integrantes",
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
        import datetime
        
        def on_date_selected(instance, value, date_range):
            fecha_str = value.strftime('%d/%m/%Y')
            if tipo == 'inicio':
                self.fecha_inicio = fecha_str
            else:
                self.fecha_final = fecha_str
        
        # Fecha mínima: 1 de enero de 2026
        min_date = datetime.date(2026, 1, 1)
        # Fecha máxima: 31 de diciembre de 2030 (por ejemplo)
        max_date = datetime.date(2030, 12, 31)
        
        # Fecha inicial sugerida
        if tipo == 'inicio':
            try:
                dia, mes, anio = map(int, self.fecha_inicio.split('/'))
                initial_date = datetime.date(anio, mes, dia)
            except:
                initial_date = min_date
        else:
            try:
                dia, mes, anio = map(int, self.fecha_final.split('/'))
                initial_date = datetime.date(anio, mes, dia)
            except:
                initial_date = min_date
        
        date_picker = MDDatePicker(
            title="Selecciona la fecha",
            min_date=min_date,
            max_date=max_date,
            year=initial_date.year,
            month=initial_date.month,
            day=initial_date.day
        )
        date_picker.bind(on_save=on_date_selected)
        date_picker.open()

class IntegrantesPagosScreen(MDScreen):
    """Pantalla para visualizar integrantes y registrar sus pagos."""
    nombre_junta = StringProperty("")
    num_personas = NumericProperty(1)

    def on_pre_enter(self):
        self.actualizar_integrantes(self.num_personas)

    def actualizar_integrantes(self, cantidad):
        self.num_personas = cantidad
        grid = self.ids.get('grid_integrantes', None)
        if not grid:
            for child in self.children:
                if hasattr(child, 'ids') and 'grid_integrantes' in child.ids:
                    grid = child.ids['grid_integrantes']
                    break
        if grid:
            grid.clear_widgets()
            for i in range(1, cantidad+1):
                card = Factory.TarjetaIntegrante()
                if i == 1:
                    card.nombre_alias = "Tú"
                    card.usuario = "Tú"
                else:
                    card.nombre_alias = "Pendiente"
                    card.usuario = "Pendiente"
                card.numero = ""
                card.posicion_numero = "left" if i%2==1 else "right"
                grid.add_widget(card)

# --- 4. CLASE PRINCIPAL DE LA APP ---

class SaviScreenManager(ScreenManager):
    """Manejador de pantallas principal."""
    pass

class SaviApp(MDApp):
    # Propiedad para controlar el estado de la moneda en el formulario
    moneda_seleccionada = StringProperty("Soles")
    
    # --- HOT RELOAD ---
    DEBUG = 1 # Activa el modo debug para recargar en caliente
    # Define los archivos KV que se vigilarán para cambios
    KV_FILES = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'design.kv')]

    def build_app(self, first=False): # <--- CAMBIO: De build() a build_app()
        """Configuración del tema y carga de la interfaz."""
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.material_style = "M3"
        
        # Solo cargamos el KV manualmente la primera vez
        # En recargas subsiguientes, HotReload ya se encarga de recargarlo
        if first:
            dir_actual = os.path.dirname(os.path.abspath(__file__))
            ruta_kv = os.path.join(dir_actual, 'design.kv')
            Builder.load_file(ruta_kv)
            
        return SaviScreenManager()

    def set_moneda(self, moneda):
        """Cambia la moneda elegida en la pestaña de Crear."""
        self.moneda_seleccionada = moneda

    def get_manager(self):
        """Helper para obtener el ScreenManager correcto, funcione o no HotReload."""
        if hasattr(self, 'root') and self.root:
            if isinstance(self.root, ScreenManager):
                return self.root
            elif hasattr(self.root, 'children'):
                for child in self.root.children:
                    if isinstance(child, ScreenManager):
                        return child
                # Fallback si no lo encuentra explícitamente pero hay hijos
                return self.root.children[0] if self.root.children else self.root
        return self.root

    def crear_junta(self, nombre, monto):
        """
        Toma los datos del formulario 'Crear' y los inyecta en la lista de 'Mis Juntas'.
        """
        if not nombre or not monto:
            # Aquí podrías mostrar un mensaje de error si los campos están vacíos
            return 

        # Accedemos a los elementos de la pantalla Home
        # USA EL HELPER AQUI
        manager = self.get_manager()
        home_screen = manager.get_screen('home')
        contenedor = home_screen.ids.lista_juntas
        mensaje_guia = home_screen.ids.mensaje_vacio

        # Al crear la primera junta, ocultamos el mensaje de 'lista vacía'
        mensaje_guia.opacity = 0
        mensaje_guia.height = 0

        # Formateamos el monto con el símbolo correspondiente
        simbolo = "S/" if self.moneda_seleccionada == "Soles" else "$"
        monto_final = f"{simbolo} {monto}"
        
        # Creamos la instancia de la tarjeta con los datos ingresados
        nueva_tarjeta = TarjetaListaJunta(
            nombre=nombre,
            monto=monto_final
        )
        
        # La agregamos al contenedor de la lista
        contenedor.add_widget(nueva_tarjeta)

        # Limpiamos los campos del formulario
        home_screen.ids.input_nombre.text = ""
        home_screen.ids.input_monto.text = ""
        
        # Cambiamos automáticamente a la pestaña 'Mis juntas' para ver el resultado
        home_screen.ids.nav_bottom.switch_tab('tab_mis_juntas')

    def ver_detalles_junta(self, nombre, monto):
        """
        Captura los datos de la junta seleccionada y los muestra en la pantalla de gestión.
        """
        manager = self.get_manager()
        detalles = manager.get_screen('detalles_junta')
        detalles.nombre_junta = nombre
        detalles.monto_junta = monto
        manager.current = 'detalles_junta'

if __name__ == '__main__':
    # Ejecución de la aplicación
    SaviApp().run()