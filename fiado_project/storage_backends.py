"""
Backends de storage para o App de Fiado.

Em desenvolvimento: usa FileSystemStorage local (padrão Django).
Em produção (Railway): usa Supabase Storage via protocolo S3.

Supabase Storage é 100% compatível com a API S3 da AWS.
"""
from storages.backends.s3boto3 import S3Boto3Storage


class SupabaseMediaStorage(S3Boto3Storage):
    """
    Storage para arquivos de mídia (fotos de clientes, QR codes).

    Utiliza o Supabase Storage com compatibilidade S3.
    Os arquivos ficam em um bucket público, acessíveis via URL direta.

    Configuração necessária no .env / Railway:
        SUPABASE_S3_KEY_ID        → S3 Access Key ID
        SUPABASE_S3_SECRET        → S3 Secret Access Key
        SUPABASE_S3_ENDPOINT      → https://<project-ref>.supabase.co/storage/v1/s3
        SUPABASE_S3_BUCKET        → nome do bucket (ex: media)
        SUPABASE_S3_PUBLIC_DOMAIN → <project-ref>.supabase.co/storage/v1/object/public/<bucket>
    """
    file_overwrite = False
    default_acl = None  # Supabase gerencia ACL via RLS policies
