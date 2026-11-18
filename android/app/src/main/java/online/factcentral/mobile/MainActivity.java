package online.factcentral.mobile;
import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import java.io.*;
import android.text.TextWatcher;
import android.text.Editable;
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
 private boolean docs=false,exp=false,audit=false;
 private int pickerGeneration=-1;
 private static final int PDF_REQUEST=81;
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
 private void login(){role="";name="";docs=false;exp=false;audit=false;frame("Iniciar sesión",false);card("Acceso seguro","Usa tu cuenta existente. Conexión HTTPS.",null);EditText space=field("Espacio administrativo",false),user=field("Usuario o correo",false),pass=field("Clave",true);
  button("Ingresar",()->{String s=space.getText().toString().trim(),u=user.getText().toString().trim(),p=pass.getText().toString();if(u.isEmpty()||p.isEmpty()){error("Completa usuario y clave.");return;}pass.setText("");task(()->{api.clear();api.login(s,u,p);return api.get("/api/v1/auth/me");},v->{JSONObject j=(JSONObject)v;role=j.optString("rol");name=j.optString("nombre");if(!RolePolicy.ROLES.contains(role)){api.clear();login();error("Rol no reconocido.");return;}if(j.optBoolean("cambio_clave_obligatorio")){api.clear();login();error("Cambia tu clave en el portal web antes de ingresar.");return;}if(role.equals("SECRETARIA")){frame("Verificando permisos",false);task(()->api.get("/api/v1/configuracion/permisos/secretaria"),x->{JSONObject f=(JSONObject)x;docs=RolePolicy.documents(role,f.optBoolean("documentos",false));exp=RolePolicy.expedients(role,f.optBoolean("expedientes",false));audit=RolePolicy.audit(role,f.optBoolean("registros",false));home();});}else{docs=RolePolicy.documents(role,true);exp=RolePolicy.expedients(role,true);audit=RolePolicy.audit(role,true);home();}});});}
 private void home(){frame("Inicio",true);card(name,role,null);if(!RolePolicy.operational(role)){card("Consola SaaS","La administración de plataforma se realiza en el portal web.",null);return;}task(()->api.get("/api/v1/dashboard/resumen"),v->{JSONObject j=(JSONObject)v;card("Expedientes",j.optString("expedientes_total","—"),exp?()->list(false):null);card("Pendientes de aprobación",j.optString("pendientes_aprobacion","—"),null);if(docs)card("Consultar documentos","Archivos y estado de revisión",()->list(true));if(exp)card("Consultar expedientes","Registros autorizados",()->list(false));});}
 private void alerts(){if(!RolePolicy.alerts(role))return;frame("Alertas",true);task(()->api.get("/api/v1/alertas?limit=50"),v->{JSONArray a=(JSONArray)v;if(a.length()==0)card("Sin alertas","No hay avisos disponibles.",null);for(int i=0;i<a.length();i++){JSONObject x=a.getJSONObject(i);card(x.optString("tipo","Alerta"),x.optString("mensaje",""),null);}});}
 private void auditPage(){if(!audit)return;frame("Fiscalización SUNAT",true);card("Observaciones","Revisión de solo lectura del Anexo 01.2. No acredita operaciones ni determina crédito fiscal.",null);button("Elegir PDF (máximo 20 MB)",()->{pickerGeneration=generation;Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/pdf");try{startActivityForResult(i,PDF_REQUEST);}catch(android.content.ActivityNotFoundException e){error("No hay selector de archivos.");}});}
 @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request!=PDF_REQUEST||result!=RESULT_OK||data==null||data.getData()==null||!audit||pickerGeneration!=generation)return;Uri uri=data.getData();frame("Revisando PDF",true);card("Procesando","Contrasta los resultados con el documento original.",null);task(()->{try(InputStream in=getContentResolver().openInputStream(uri);ByteArrayOutputStream out=new ByteArrayOutputStream()){if(in==null)throw new IOException("No se pudo abrir el archivo.");byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1){if(out.size()+n>20*1024*1024)throw new IOException("El PDF supera 20 MB.");out.write(b,0,n);}return api.reviewPdf(out.toByteArray());}},v->{JSONObject j=(JSONObject)v;frame("Fiscalización SUNAT",true);card("Pendiente de verificación","No acredita operaciones ni determina crédito fiscal.",null);card("Filas leídas / no leídas",j.optString("filas_leidas")+" / "+j.optString("filas_no_leidas"),null);card("Proveedores",j.optString("proveedores"),null);card("Base observada",j.optString("base_observada"),null);card("IGV observado",j.optString("igv_observado"),null);card("Total observado",j.optString("total_observado"),null);card("Diferencias aritméticas",j.optString("filas_con_diferencia_aritmetica"),null);JSONObject p=j.optJSONObject("periodos");if(p!=null){java.util.Iterator<String> keys=p.keys();while(keys.hasNext()){String key=keys.next();card(key,p.optString(key)+" filas",null);}}button("Revisar otro PDF",this::auditPage);});}
 private void list(boolean document){if(document?!docs:!exp){error("Acceso no autorizado.");return;}frame(document?"Documentos":"Expedientes",true);task(()->api.get(document?"/api/v1/documentos?limit=50":"/api/v1/expedientes?limit=50"),v->{JSONArray a=(JSONArray)v;if(a.length()==0){card("Sin resultados","No hay registros disponibles.",null);return;}for(int i=0;i<a.length();i++){JSONObject j=a.getJSONObject(i);String title=document?j.optString("nombre_original","Documento"):j.optString("serie")+"-"+j.optString("correlativo");card(title,j.optString("estado","Sin estado")+" · "+j.optString("fecha_emision",""),null);}card("Consulta","Primeros 50 registros autorizados.",null);});}
 private void more(){frame("Más",true);card(name,role,null);if(audit)card("Fiscalización SUNAT","Resumen de observaciones · solo lectura",this::auditPage);if(RolePolicy.alerts(role))card("Alertas","Consultar avisos del servidor",this::alerts);button("Actualizar sesión",()->{api.clear();login();});button("Cerrar sesión",()->{frame("Cerrando sesión",false);task(()->{try{api.logout();}catch(Exception ignored){}finally{api.clear();}return new JSONObject();},v->login());});}
 @Override protected void onDestroy(){generation++;worker.shutdownNow();super.onDestroy();}
}
