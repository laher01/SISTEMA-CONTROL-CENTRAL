package online.factcentral.mobile;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.json.*;
final class Api {
 static final String BASE="https://factcentral.online";
 private final CookieManager cookies=new CookieManager(null,CookiePolicy.ACCEPT_ORIGINAL_SERVER);
 synchronized Object get(String route)throws Exception{return request(route,null);}
 synchronized JSONObject login(String space,String login,String password)throws Exception{
  JSONObject p=new JSONObject().put("espacio",space.isEmpty()?JSONObject.NULL:space).put("login",login).put("clave",password);
  return (JSONObject)request("/api/v1/auth/login",p);
 }
 synchronized void logout()throws Exception{try{request("/api/v1/auth/logout",new JSONObject());}finally{cookies.getCookieStore().removeAll();}}
 synchronized void clear(){cookies.getCookieStore().removeAll();}
 private Object request(String route,JSONObject body)throws Exception{
  if(!route.startsWith("/api/v1/")||route.contains("..")||route.contains("\\"))throw new IOException("Ruta inválida");
  URI uri=URI.create(BASE+route);
  HttpURLConnection c=(HttpURLConnection)uri.toURL().openConnection();
  c.setInstanceFollowRedirects(false);c.setConnectTimeout(15000);c.setReadTimeout(20000);
  c.setRequestProperty("Accept","application/json");c.setRequestProperty("Origin",BASE);c.setRequestProperty("Referer",BASE+"/");
  for(var e:cookies.get(uri,Collections.emptyMap()).entrySet())for(String v:e.getValue())c.addRequestProperty(e.getKey(),v);
  try{
   if(body!=null){c.setRequestMethod("POST");c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");try(OutputStream o=c.getOutputStream()){o.write(body.toString().getBytes(StandardCharsets.UTF_8));}}
   int code=c.getResponseCode();
   cookies.put(uri,c.getHeaderFields());
   if(code==401){clear();throw new IOException("Sesión vencida. Vuelve a ingresar.");}
   if(code==403)throw new IOException("Acceso no autorizado.");
   if(code<200||code>=300)throw new IOException("No se pudo completar la consulta ("+code+").");
   if(code==204)return new JSONObject();
   try(InputStream in=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
    byte[] buf=new byte[8192];int n;while((n=in.read(buf))!=-1){if(out.size()+n>8*1024*1024)throw new IOException("Respuesta demasiado extensa");out.write(buf,0,n);}
    if(out.size()==0)return new JSONObject();
    return new JSONTokener(out.toString("UTF-8")).nextValue();
   }
  }finally{c.disconnect();}
 }
}
