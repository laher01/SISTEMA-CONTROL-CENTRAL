package online.factcentral.mobile;
import java.util.Set;
import java.util.HashSet;
import java.util.Arrays;
final class RolePolicy {
 private static Set<String> set(String... values){return new HashSet<>(Arrays.asList(values));}
 static final Set<String> ROLES=set("SUPERADMIN","ADMINISTRADOR","SECRETARIA","GERENTE","RESPONSABLE","USUARIO","GESTOR");
 static boolean operational(String role){return ROLES.contains(role)&&!role.equals("SUPERADMIN");}
 static boolean documents(String role,boolean enabled){return set("ADMINISTRADOR","USUARIO","GESTOR").contains(role)||(role.equals("SECRETARIA")&&enabled);}
 static boolean upload(String role){return "GESTOR".equals(role);}
 static boolean remove(String role){return set("ADMINISTRADOR","USUARIO","GESTOR").contains(role);}
 static boolean expedients(String role,boolean enabled){return operational(role)&&(!role.equals("SECRETARIA")||enabled);}
 static boolean audit(String role,boolean enabled){return set("ADMINISTRADOR","GERENTE").contains(role)||(role.equals("SECRETARIA")&&enabled);}
 static boolean alerts(String role){return set("ADMINISTRADOR","SECRETARIA","RESPONSABLE","USUARIO","GESTOR").contains(role);}
}
