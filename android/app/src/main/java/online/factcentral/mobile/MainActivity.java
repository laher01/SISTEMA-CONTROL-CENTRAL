package online.factcentral.mobile;
import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.View;
import android.view.WindowManager;
import android.widget.*;
import android.text.InputType;
import java.util.concurrent.*;
import org.json.*;
public class MainActivity extends Activity {
 private final Api api=new Api();
 private final ExecutorService worker=Executors.newSingleThreadExecutor();
 private LinearLayout root,body,nav;
 private String role="",name="";
 private boolean docs=false,exp=false;
 private int generation=0;
 private final int navy=Color.rgb(16,51,80),teal=Color.rgb(0,128,117),bg=Color.rgb(242,246,250);
 @Override public void onCreate(Bundle b){super.onCreate(b);getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);getWindow().setStatusBarColor(navy);getWindow().setNavigationBarColor(navy);login();}
 private int dp(int x){return (int)(x*getResources().getDisplayMetrics().density+0.5f);}
 private GradientDrawable shape(int color){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(14));return d;}
 private TextView text(String s,int size,int color,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);if(bold)t.setTypeface(null,Typeface.BOLD);return t;}
 private LinearLayout vertical(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l;}
 private void frame(String heading,boolean menu){
  generation++;root=vertical();root.setBackgroundColor(bg);setContentView(root);
  LinearLayout top=vertical();top.setBackgroundColor(navy);top.setPadding(dp(20),dp(16),dp(20),dp(16));top.addView(text("FACT CENTRAL",18,Color.WHITE,true));top.addView(text(heading,26,Color.WHITE,true));root.addView(top);
  ScrollView scroll=new ScrollView(this);body=vertical();body.setPadding(dp(16),dp(16),dp(16),dp(16));scroll.addView(body);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
  if(menu){nav=new LinearLayout(this);nav.setBackgroundColor(Color.WHITE);root.addView(nav);if(RolePolicy.operational(role)){tab("Inicio",this::home);if(docs)tab("Documentos",()->list(true));if(exp)tab("Expedientes",()->list(false));}tab("Más",this::more);}
 }
 private void tab(String label,Runnable action){TextView t=text(label,13,navy,true);t.setGravity(android.view.Gravity.CENTER);t.setPadding(dp(3),dp(15),dp(3),dp(15));t.setOnClickListener(v->action.run());nav.addView(t,new LinearLayout.LayoutParams(0,-2,1));}
 private void card(String title,String detail,Runnable action){LinearLayout box=vertical();box.setBackground(shape(Color.WHITE));box.setPadding(dp(16),dp(16),dp(16),dp(16));box.addView(text(title,19,navy,true));box.addView(text(detail,15,Color.DKGRAY,false));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(10);body.addView(box,p);if(action!=null){box.setClickable(true);box.setOnClickListener(v->action.run());}}
 private EditText field(String hint,boolean password){EditText e=new EditText(this);e.setHint(hint);e.setSingleLine(true);if(password)e.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);body.addView(e);return e;}
 private void button(String label,Runnable action){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setOnClickListener(v->action.run());body.addView(b);}
 private interface Job{Object run()throws Exception;}
 private interface Result{void show(Object value)throws Exception;}
 private void task(Job job,Result result){
  int current=generation;worker.execute(()->{try{Object value=job.run();runOnUiThread(()->{if(current!=generation||isFinishing())return;try{result.show(value);}catch(Exception e){error("Respuesta no válida.");}});}catch(Exception e){runOnUiThread(()->{if(current==generation&&!isFinishing())error(e instanceof java.io.IOException?e.getMessage():"No se pudo completar la operación.");});}});
 }
 private void error(String msg){card("Aviso",msg,null);}
 private void login(){role="";name="";docs=false;exp=false;frame("Iniciar sesión",false);card("Acceso seguro","Usa tu cuenta existente. Conexión HTTPS.",null);EditText space=field("Espacio administrativo",false),user=field("Usuario o correo",false),pass=field("Clave",true);
  button("Ingresar",()->{String s=space.getText().toString().trim(),u=user.getText().toString().trim(),p=pass.getText().toString();if(u.isEmpty()||p.isEmpty()){error("Completa usuario y clave.");return;}pass.setText("");task(()->{api.clear();api.login(s,u,p);return api.get("/api/v1/auth/me");},v->{JSONObject j=(JSONObject)v;role=j.optString("rol");name=j.optString("nombre");if(!RolePolicy.ROLES.contains(role)){api.clear();login();error("Rol no reconocido.");return;}if(j.optBoolean("cambio_clave_obligatorio")){api.clear();login();error("Cambia tu clave en el portal web antes de ingresar.");return;}if(role.equals("SECRETARIA")){frame("Verificando permisos",false);task(()->api.get("/api/v1/configuracion/permisos/secretaria"),x->{JSONObject f=(JSONObject)x;docs=RolePolicy.documents(role,f.optBoolean("documentos",false));exp=RolePolicy.expedients(role,f.optBoolean("expedientes",false));home();});}else{docs=RolePolicy.documents(role,true);exp=RolePolicy.expedients(role,true);home();}});});}
 private void home(){frame("Inicio",true);card(name,role,null);if(!RolePolicy.operational(role)){card("Consola SaaS","La administración de plataforma se realiza en el portal web.",null);return;}task(()->api.get("/api/v1/dashboard/resumen"),v->{JSONObject j=(JSONObject)v;card("Expedientes",j.optString("expedientes_total","—"),exp?()->list(false):null);card("Pendientes de aprobación",j.optString("pendientes_aprobacion","—"),null);if(docs)card("Consultar documentos","Archivos y estado de revisión",()->list(true));if(exp)card("Consultar expedientes","Registros autorizados",()->list(false));});}
 private void list(boolean document){if(document?!docs:!exp){error("Acceso no autorizado.");return;}frame(document?"Documentos":"Expedientes",true);task(()->api.get(document?"/api/v1/documentos?limit=50":"/api/v1/expedientes?limit=50"),v->{JSONArray a=(JSONArray)v;if(a.length()==0){card("Sin resultados","No hay registros disponibles.",null);return;}for(int i=0;i<a.length();i++){JSONObject j=a.getJSONObject(i);String title=document?j.optString("nombre_original","Documento"):j.optString("serie")+"-"+j.optString("correlativo");card(title,j.optString("estado","Sin estado")+" · "+j.optString("fecha_emision",""),null);}card("Consulta","Primeros 50 registros autorizados.",null);});}
 private void more(){frame("Más",true);card(name,role,null);button("Actualizar sesión",()->{api.clear();login();});button("Cerrar sesión",()->{frame("Cerrando sesión",false);task(()->{try{api.logout();}catch(Exception ignored){}finally{api.clear();}return new JSONObject();},v->login());});}
 @Override protected void onDestroy(){generation++;worker.shutdownNow();super.onDestroy();}
}
