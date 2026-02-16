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
from kivy.utils import platform
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Tipado para que Pylance reconozca módulos Android en tiempo de análisis.
    from jnius import autoclass  # type: ignore
    # `android.permissions` es un módulo disponible sólo en Android empaquetado;
    # lo importamos dinámicamente en tiempo de ejecución para evitar errores
    # del analizador estático en el entorno de desarrollo.

# --- CONFIGURACIÓN DE VENTANA ---
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
Config.set('graphics', 'resizable', '0')

from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.label import MDLabel

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


class FitLabel(MDLabel):
    """Etiqueta que ajusta su `font_size` para que el texto quepa en el ancho.

    Ajusta el tamaño de letra decreciendo desde `max_font_size` hasta
    `min_font_size` en pasos definidos.
    """
    max_font_size = NumericProperty(72)
    min_font_size = NumericProperty(24)
    step = NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(lambda dt: self._adjust())

    def on_size(self, *args):
        Clock.schedule_once(lambda dt: self._adjust(), 0)

    def on_text(self, *args):
        Clock.schedule_once(lambda dt: self._adjust(), 0)

    def _adjust(self, *l):
        try:
            fs = self.max_font_size
            self.font_size = fs
            padding = dp(20)
            # actualizar textura y reducir hasta que quepa
            self.texture_update()
            # Si ancho no está disponible aún, salir
            if not self.width or self.width <= 0:
                return
            while fs > self.min_font_size:
                self.texture_update()
                if self.texture_size[0] <= (self.width - padding) or self.texture_size[0] == 0:
                    break
                fs -= self.step
                self.font_size = fs
        except Exception:
            pass

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog_integrantes = None

    def on_pre_enter(self):
        """Sincronizar el número visual con la lista real al entrar."""
        app = MDApp.get_running_app()
        # Usamos self.manager directamente en lugar de app.get_manager() por seguridad
        if self.manager:
            try:
                pagos = self.manager.get_screen('integrantes_pagos')
                if pagos and hasattr(pagos, 'lista_cupos'):
                    self.num_personas = str(len(pagos.lista_cupos))
            except Exception as e:
                print(f"Error sincronizando integrantes: {e}")

    def abrir_dialogo_editar_integrantes(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.textfield import MDTextField
        from kivymd.toast import toast # Asegúrate de importar toast
        
        if self.dialog_integrantes:
            self.dialog_integrantes.dismiss()
        
        app = MDApp.get_running_app()
        pagos = self.manager.get_screen('integrantes_pagos')
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
        """Abre un selector de fechas para actualizar fecha_inicio o fecha_final."""
        from kivymd.uix.pickers import MDDatePicker

        def on_date_selected(instance, value, date_range):
            fecha_str = value.strftime('%d/%m/%Y')
            if tipo == 'inicio':
                self.fecha_inicio = fecha_str
            else:
                self.fecha_final = fecha_str

        # Importante: MDDatePicker a veces requiere parámetros según la versión de KivyMD
        date_picker = MDDatePicker()
        date_picker.bind(on_save=on_date_selected)
        date_picker.open()

class SorteoScreen(MDScreen):
    pass

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
                'dni': '', 'telefono': '', 'correo': '',
                'numero': '1'
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
                    'dni': '', 'telefono': '', 'correo': '',
                    'numero': ''
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
                # Asignar número disponible (1 reservado para organizador)
                try:
                    usados = {int(c.get('numero')) for c in self.lista_cupos if c.get('numero')}
                except Exception:
                    usados = set()
                max_num = len(self.lista_cupos)
                asignado = None
                for n in range(2, max_num + 1):
                    if n not in usados:
                        asignado = n
                        break
                if asignado is None:
                    asignado = max_num
                nuevo_cupo['numero'] = str(asignado)

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

    # --- SORTEO / NÚMEROS ---
    def generar_sorteo(self):
        """Genera números aleatorios para los integrantes (organizador = 1).

        Solo redistribuye números entre los integrantes ocupados (excluye organizador).
        """
        import random
        app = MDApp.get_running_app()
        max_num = len(self.lista_cupos)
        # participantes ocupados excepto índice 0
        participantes = [ (i, c) for i,c in enumerate(self.lista_cupos) if c.get('ocupado') and i != 0 ]
        if not participantes:
            toast('No hay integrantes para sortear')
            return

        numeros_disponibles = list(range(2, max_num+1))
        random.shuffle(numeros_disponibles)

        for (i, _), num in zip(participantes, numeros_disponibles):
            self.lista_cupos[i]['numero'] = str(num)

        self.renderizar_lista()
        toast('Números asignados aleatoriamente')

    def abrir_dialogo_intercambio(self):
        """Abre un diálogo simple para intercambiar números entre integrantes.

        Solo el creador (app.is_creator) puede ejecutar el intercambio.
        """
        app = MDApp.get_running_app()
        if not getattr(app, 'is_creator', False):
            toast('Solo el dueño de la junta puede cambiar números')
            return

        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
        from kivymd.uix.textfield import MDTextField

        campo_a = MDTextField(hint_text='Número actual (ej: 2)')
        campo_b = MDTextField(hint_text='Número a intercambiar (ej: 3)')
        contenido = MDBoxLayout(orientation='vertical', spacing='8dp', adaptive_height=True)
        contenido.add_widget(campo_a)
        contenido.add_widget(campo_b)

        def intercambiar(obj):
            a = campo_a.text.strip()
            b = campo_b.text.strip()
            if not a.isdigit() or not b.isdigit():
                toast('Ingrese números válidos')
                return
            na = a; nb = b
            idx_a = next((i for i,c in enumerate(self.lista_cupos) if c.get('numero') == na), None)
            idx_b = next((i for i,c in enumerate(self.lista_cupos) if c.get('numero') == nb), None)
            if idx_a is None or idx_b is None:
                toast('Uno de los números no existe')
                return
            # impedir cambiar el organizador (numero 1)
            if na == '1' or nb == '1':
                toast('No se puede cambiar el número del organizador')
                return
            # swap
            self.lista_cupos[idx_a]['numero'], self.lista_cupos[idx_b]['numero'] = self.lista_cupos[idx_b]['numero'], self.lista_cupos[idx_a]['numero']
            self.renderizar_lista()
            dialog.dismiss()
            toast('Intercambio realizado')

        dialog = MDDialog(
            title='Intercambiar Números',
            type='custom',
            content_cls=contenido,
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: dialog.dismiss()),
                MDFillRoundFlatButton(text='INTERCAMBIAR', on_release=intercambiar)
            ]
        )
        dialog.open()

    def solicitar_intercambio_participante(self):
        """Permite a un participante enviar una solicitud de intercambio al dueño.

        Pide al usuario su número y el número del otro integrante y guarda la
        solicitud en `app.pending_swap_requests`.
        """
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
        from kivymd.uix.textfield import MDTextField

        campo_mio = MDTextField(hint_text='Tu número (ej: 2)')
        campo_otro = MDTextField(hint_text='Número con quien quieres cambiar (ej: 3)')
        contenido = MDBoxLayout(orientation='vertical', spacing='8dp', adaptive_height=True)
        contenido.add_widget(campo_mio)
        contenido.add_widget(campo_otro)

        app = MDApp.get_running_app()

        def enviar(obj):
            a = campo_mio.text.strip()
            b = campo_otro.text.strip()
            if not a.isdigit() or not b.isdigit():
                toast('Ingrese números válidos')
                return
            if a == '1' or b == '1':
                toast('No se puede solicitar intercambio con el organizador')
                return
            # Guardar solicitud
            req = {'from': a, 'to': b}
            app.pending_swap_requests.append(req)
            dialog.dismiss()
            toast('Solicitud enviada al dueño de la junta')

        dialog = MDDialog(
            title='Solicitar Intercambio',
            type='custom',
            content_cls=contenido,
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: dialog.dismiss()),
                MDFillRoundFlatButton(text='ENVIAR', on_release=enviar)
            ]
        )
        dialog.open()

    def ver_solicitudes_intercambio(self):
        """Permite al dueño procesar las solicitudes pendientes una a una."""
        app = MDApp.get_running_app()
        if not getattr(app, 'is_creator', False):
            toast('Solo el dueño de la junta puede ver las solicitudes')
            return

        if not app.pending_swap_requests:
            toast('No hay solicitudes pendientes')
            return

        # Procesar la primera solicitud en cola
        req = app.pending_swap_requests.pop(0)
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
        contenido = MDBoxLayout(orientation='vertical', spacing='6dp', adaptive_height=True)
        contenido.add_widget(MDLabel(text=f"Solicitud: {req['from']} ⇄ {req['to']}", theme_text_color='Primary'))

        def aprobar(obj):
            na = req['from']; nb = req['to']
            idx_a = next((i for i,c in enumerate(self.lista_cupos) if c.get('numero') == na), None)
            idx_b = next((i for i,c in enumerate(self.lista_cupos) if c.get('numero') == nb), None)
            if idx_a is None or idx_b is None:
                toast('Uno de los números ya no existe')
            else:
                # swap
                self.lista_cupos[idx_a]['numero'], self.lista_cupos[idx_b]['numero'] = self.lista_cupos[idx_b]['numero'], self.lista_cupos[idx_a]['numero']
                self.renderizar_lista()
                toast('Solicitud aprobada: números intercambiados')
            dialog.dismiss()
            # llamar recursivamente para seguir procesando
            Clock.schedule_once(lambda dt: self.ver_solicitudes_intercambio(), 0.2)

        def rechazar(obj):
            toast('Solicitud rechazada')
            dialog.dismiss()
            Clock.schedule_once(lambda dt: self.ver_solicitudes_intercambio(), 0.2)

        dialog = MDDialog(
            title='Procesar Solicitud de Intercambio',
            type='custom',
            content_cls=contenido,
            buttons=[
                MDFlatButton(text='RECHAZAR', on_release=rechazar),
                MDFillRoundFlatButton(text='APROBAR', on_release=aprobar)
            ]
        )
        dialog.open()

    def _aprobar_solicitud(self, req):
        """Procesa (aprueba) una solicitud de intercambio proporcionada por el owner."""
        try:
            na = req['from']; nb = req['to']
            idx_a = next((i for i,c in enumerate(self.lista_cupos) if c.get('numero') == na), None)
            idx_b = next((i for i,c in enumerate(self.lista_cupos) if c.get('numero') == nb), None)
            if idx_a is None or idx_b is None:
                toast('Uno de los números ya no existe')
                return False
            if na == '1' or nb == '1':
                toast('No se puede cambiar el número del organizador')
                return False
            self.lista_cupos[idx_a]['numero'], self.lista_cupos[idx_b]['numero'] = self.lista_cupos[idx_b]['numero'], self.lista_cupos[idx_a]['numero']
            self.renderizar_lista()
            return True
        except Exception as e:
            print('Error _aprobar_solicitud:', e)
            return False

    def mostrar_dialogo_edicion(self, indice, es_registro_qr=False):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.label import MDLabel
        
        datos_actuales = {}
        if not es_registro_qr and indice >= 0:
            if indice < len(self.lista_cupos):
                datos_actuales = self.lista_cupos[indice]
        
        campo_nombre = MDTextField(hint_text="Nombre Completo", text=datos_actuales.get('nombre', ''), input_filter=None)
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
    DEBUG = 0
    def build(self):
        # Configurar tema
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.material_style = "M3"

        # inicializar lista de solicitudes de intercambio
        self.pending_swap_requests = []
        self.is_creator = True

        # Cargamos el archivo explícitamente pero manejando errores de ruta
        try:
            Builder.load_file('design.kv')
        except Exception as e:
            print(f'Error crítico en design.kv: {e}')

        return SaviScreenManager()

    def on_start(self):
        """Solicitar permisos en Android al iniciar la app."""
        if platform == 'android':
            try:
                import importlib

                permissions = importlib.import_module('android.permissions')
                request_permissions = getattr(permissions, 'request_permissions', None)
                Permission = getattr(permissions, 'Permission', None)

                if request_permissions and Permission:
                    permisos = [
                        Permission.CAMERA,
                        Permission.READ_EXTERNAL_STORAGE,
                        Permission.WRITE_EXTERNAL_STORAGE,
                        Permission.READ_CONTACTS,
                    ]

                    request_permissions(permisos)
                else:
                    print('android.permissions no encontrado o incompleto en runtime')
            except Exception as e:
                print('No se pudieron solicitar permisos runtime:', e)

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

    # --- Sorteo inline helpers (muestra UI dentro del Card de Sorteo) ---
    def mostrar_formulario_solicitud(self):
        try:
            pantalla = self.get_manager().get_screen('sorteo')
            sorteo_area = pantalla.ids.get('sorteo_area')
            if not sorteo_area:
                return
            sorteo_area.clear_widgets()

            from kivymd.uix.textfield import MDTextField
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDRectangleFlatButton

            campo_mio = MDTextField(hint_text='Tu número (ej: 2)')
            campo_otro = MDTextField(hint_text='Número objetivo (ej: 3)')
            row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
            enviar = MDRectangleFlatButton(text='Enviar', on_release=lambda x: self._enviar_solicitud_inline(campo_mio.text, campo_otro.text))
            cancelar = MDRectangleFlatButton(text='Cancelar', on_release=lambda x: sorteo_area.clear_widgets())

            sorteo_area.add_widget(campo_mio)
            sorteo_area.add_widget(campo_otro)
            row.add_widget(enviar)
            row.add_widget(cancelar)
            sorteo_area.add_widget(row)
        except Exception as e:
            print('Error mostrar_formulario_solicitud:', e)

    def _enviar_solicitud_inline(self, a, b):
        try:
            if not a or not b:
                toast('Complete ambos campos')
                return
            if not a.isdigit() or not b.isdigit():
                toast('Ingrese números válidos')
                return
            if a == '1' or b == '1':
                toast('No se puede solicitar intercambio con el organizador')
                return

            req = {'from': a, 'to': b}
            self.pending_swap_requests.append(req)
            toast('Solicitud enviada al dueño de la junta')
            pantalla = self.get_manager().get_screen('sorteo')
            sorteo_area = pantalla.ids.get('sorteo_area')
            if sorteo_area:
                sorteo_area.clear_widgets()
        except Exception as e:
            print('Error _enviar_solicitud_inline:', e)

    def mostrar_solicitudes_sorteo(self):
        try:
            pantalla = self.get_manager().get_screen('sorteo')
            sorteo_area = pantalla.ids.get('sorteo_area')
            if not sorteo_area:
                return
            sorteo_area.clear_widgets()

            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDRectangleFlatButton
            from kivymd.uix.label import MDLabel

            app = self
            if not getattr(app, 'is_creator', False):
                sorteo_area.add_widget(MDLabel(text='Solo el dueño puede ver las solicitudes', halign='center'))
                return

            if not self.pending_swap_requests:
                sorteo_area.add_widget(MDLabel(text='No hay solicitudes pendientes', halign='center'))
                return

            for i, req in enumerate(list(self.pending_swap_requests)):
                row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
                row.add_widget(MDLabel(text=f"{req['from']} ⇄ {req['to']}", halign='left'))
                btn_ap = MDRectangleFlatButton(text='Aprobar', on_release=lambda x, r=req: self._procesar_solicitud_inline(r, True))
                btn_re = MDRectangleFlatButton(text='Rechazar', on_release=lambda x, r=req: self._procesar_solicitud_inline(r, False))
                row.add_widget(btn_ap)
                row.add_widget(btn_re)
                sorteo_area.add_widget(row)
        except Exception as e:
            print('Error mostrar_solicitudes_sorteo:', e)

    def _procesar_solicitud_inline(self, req, aprobar):
        try:
            try:
                self.pending_swap_requests.remove(req)
            except ValueError:
                pass

            pagos = self.get_manager().get_screen('integrantes_pagos')
            if aprobar:
                ok = pagos._aprobar_solicitud(req)
                if ok:
                    toast('Solicitud aprobada: números intercambiados')
                else:
                    toast('No se pudo aprobar la solicitud')
            else:
                toast('Solicitud rechazada')

            self.mostrar_solicitudes_sorteo()
        except Exception as e:
            print('Error procesar solicitud inline:', e)

    # --- File manager para subir imagen QR ---
    def abrir_file_manager(self, start_path=None):
        from kivymd.uix.filemanager import MDFileManager
        if not start_path:
            start_path = os.path.expanduser('~')

        def _exit_manager(*args):
            try:
                self.file_manager.close()
            except Exception:
                pass

        self.file_manager = MDFileManager(
            select_path=self._select_path,
            exit_manager=_exit_manager,
            preview=True,
        )
        try:
            self.file_manager.show(start_path)
        except Exception as e:
            print('FileManager error:', e)

    def lanzar_scanner(self):
        """Lanza una app externa de escaneo (ZXing) en Android o informa alternativas."""
        if platform == 'android':
            try:
                try:
                    from jnius import autoclass  # type: ignore
                except Exception:
                    autoclass = None

                if autoclass is None:
                    raise Exception("El módulo 'jnius' no está disponible.")

                Intent = autoclass('android.content.Intent')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity

                intent = Intent('com.google.zxing.client.android.SCAN')
                # try to start external scanner
                activity.startActivity(intent)
                toast('Abriendo escáner externo...')
                return
            except Exception as e:
                print('No se pudo lanzar ZXing intent:', e)
                toast('No hay app de escaneo instalada o falta el módulo jnius. Usa SUBIR QR o ingresa el código.')
                return
        else:
            toast('Escaneo sólo disponible en Android. Usa SUBIR QR o ingresa el código.')

    def _select_path(self, path):
        """Callback when a file is selected from MDFileManager."""
        try:
            # Intentar actualizar la vista de Invitar
            manager = self.get_manager()
            try:
                invitar = manager.get_screen('invitar')
                if invitar and hasattr(invitar, 'ids') and 'img_qr' in invitar.ids:
                    invitar.ids.img_qr.source = path
                    try:
                        invitar.ids.img_qr.reload()
                    except Exception:
                        pass
            except Exception:
                pass

            # Intentar actualizar la previsualización en la pestaña Unirse (Home)
            try:
                home = manager.get_screen('home')
                if home and hasattr(home, 'ids') and 'img_qr_unirse' in home.ids:
                    home.ids.img_qr_unirse.source = path
                    try:
                        home.ids.img_qr_unirse.reload()
                    except Exception:
                        pass
            except Exception:
                pass

            toast('Imagen QR cargada')
        except Exception as e:
            print('Error al seleccionar archivo:', e)
            toast('Error al cargar imagen')

    def crear_junta(self, nombre, monto, cantidad, periodo, inicio, final):
        if not (nombre and nombre.strip()) or not (monto and str(monto).strip()):
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

        # Marcar que el dispositivo actual es el creador de la junta
        try:
            self.is_creator = True
        except Exception:
            self.is_creator = True

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

        # Validación local: formato SAVI-0000 o URL que contenga SAVI-0000
        pattern = re.compile(r"SAVI-\d{4}")
        m = pattern.search(codigo)
        if not m:
            toast("Código inválido. Formato esperado: SAVI-1234")
            return

        codigo_valido = m.group(0)

        # Preparar previsualización con datos locales (mock si no hay servidor)
        try:
            manager = self.get_manager()
            pagos_screen = manager.get_screen('integrantes_pagos')
            # determinar cupos disponibles si es posible
            capacidad = len(pagos_screen.lista_cupos) if pagos_screen.lista_cupos else None
            ocupados = sum(1 for c in pagos_screen.lista_cupos if c.get('ocupado')) if pagos_screen.lista_cupos else 0

            nombre = f"Junta {codigo_valido}"
            monto = "S/ 100.00"
            organizador = "Organizador Ejemplo"
            periodo = "Mensual"
            cupos_text = f"{ocupados}/{capacidad}" if capacidad is not None else "Desconocido"

            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton, MDFillRoundFlatButton
            from kivymd.uix.label import MDLabel

            contenido = MDBoxLayout(orientation='vertical', spacing='8dp', adaptive_height=True)
            contenido.add_widget(MDLabel(text=f"Nombre: {nombre}", theme_text_color='Primary'))
            contenido.add_widget(MDLabel(text=f"Monto: {monto}", theme_text_color='Primary'))
            contenido.add_widget(MDLabel(text=f"Organizador: {organizador}", theme_text_color='Primary'))
            contenido.add_widget(MDLabel(text=f"Periodo: {periodo}", theme_text_color='Primary'))
            contenido.add_widget(MDLabel(text=f"Cupos: {cupos_text}", theme_text_color='Secondary'))

            def solicitar_unirse(obj):
                try:
                    if not pagos_screen.lista_cupos:
                        pagos_screen.inicializar_datos_default(0)

                    def lanzar_formulario(dt):
                        pagos_screen.mostrar_dialogo_edicion(-1, es_registro_qr=True)

                    Clock.schedule_once(lanzar_formulario, 0.2)
                    dialog.dismiss()
                except Exception as e:
                    print('Error al solicitar unirse:', e)
                    toast('Error al solicitar unirse')

            dialog = MDDialog(
                title='Confirmar unión',
                type='custom',
                content_cls=contenido,
                buttons=[
                    MDFlatButton(text='CANCELAR', on_release=lambda x: dialog.dismiss()),
                    MDFillRoundFlatButton(text='SOLICITAR UNIRSE', on_release=solicitar_unirse),
                ]
            )
            dialog.open()

        except Exception as e:
            print(f"Error: {e}")
            toast("Error al procesar.")

if __name__ == '__main__':
    SaviApp().run()