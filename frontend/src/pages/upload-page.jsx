import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileImage, ScanSearch, UploadCloud, ZoomIn } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/shared/page-header";
import { multimodalApi, transactionApi } from "@/lib/api";

export function UploadPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [fields, setFields] = useState({
    date: "",
    amount: "",
    gst_amount: "",
    vendor: "",
    category: "General",
    type: "purchase",
  });

  const typesQuery = useQuery({
    queryKey: ["transaction-types"],
    queryFn: () => transactionApi.getTypes().then((res) => res.data.types || []),
  });

  const scanMutation = useMutation({
    mutationFn: async (nextFile) => {
      const upload = await multimodalApi.upload(nextFile, "");
      const ocr = await multimodalApi.ocr(upload.data.id);
      return ocr.data;
    },
    onSuccess: (data) => {
      const extracted = data.extracted_data || {};
      setFields({
        date: normalizeDate(extracted.date),
        amount: extracted.amount ?? "",
        gst_amount: extracted.gst_amount ?? "",
        vendor: extracted.vendor ?? "",
        category: extracted.category || "General",
        type: extracted.type === "expense" ? "purchase" : "sales",
      });
      toast.success("Bill scanned. Review the extracted fields before saving.");
    },
    onError: () => toast.error("Bill could not be read."),
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      transactionApi.create({
        amount: Number(fields.amount || 0),
        category: fields.category,
        type: fields.type,
        quantity: null,
        gst_amount: Number(fields.gst_amount || 0) || null,
        description: fields.vendor || null,
        date: fields.date || null,
      }),
    onSuccess: () => {
      toast.success("Bill saved as a transaction.");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Could not save the scanned bill."),
  });

  const processing = scanMutation.isPending;
  const previewTitle = useMemo(() => (file ? file.name : "No file selected"), [file]);

  const handleFile = (nextFile) => {
    setFile(nextFile);
    setPreview(URL.createObjectURL(nextFile));
    scanMutation.mutate(nextFile);
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Bill Scanner" description="Drop a bill or invoice here, review OCR fields, and save it as a transaction." />

      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <Card className="relative overflow-hidden">
          <CardHeader>
            <CardTitle>Upload Zone</CardTitle>
            <CardDescription>Works best with clear bill or invoice images.</CardDescription>
          </CardHeader>
          <CardContent>
            <label className="relative flex min-h-[420px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/70 p-8 text-center dark:border-slate-700 dark:bg-slate-950/40">
              {preview ? (
                <div className="relative h-full w-full overflow-hidden rounded-2xl">
                  <img src={preview} alt={previewTitle} className="mx-auto max-h-[360px] rounded-2xl object-contain" />
                  {processing ? <div className="absolute inset-x-10 top-0 h-1 animate-pulse bg-assistant shadow-[0_0_40px_#0EA5E9]" /> : null}
                </div>
              ) : (
                <>
                  <UploadCloud className="h-12 w-12 text-slate-400" />
                  <p className="mt-4 text-lg font-semibold">Drop your bill or invoice here</p>
                  <p className="mt-2 max-w-sm text-sm text-slate-500">Scan GST invoices, shop bills, or supplier receipts and review the extracted fields before saving.</p>
                </>
              )}
              <input type="file" hidden accept="image/*" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
            </label>
            {processing ? <p className="mt-4 text-sm text-assistant">Reading your bill...</p> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Extracted Fields</CardTitle>
            <CardDescription>Editable preview before transaction save</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              ["Bill Date", "date"],
              ["Total Amount", "amount"],
              ["GST Amount", "gst_amount"],
              ["Vendor Name", "vendor"],
              ["Category", "category"],
            ].map(([label, key]) => (
              <div key={key}>
                <Label>{label}</Label>
                <Input value={fields[key]} onChange={(e) => setFields((prev) => ({ ...prev, [key]: e.target.value }))} />
              </div>
            ))}

            <div>
              <Label>Transaction Type</Label>
              <select
                className="h-11 w-full rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50"
                value={fields.type}
                onChange={(e) => setFields((prev) => ({ ...prev, type: e.target.value }))}
              >
                {(typesQuery.data || []).map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Button variant="success" onClick={() => saveMutation.mutate()} disabled={!fields.amount}>
                <ScanSearch className="h-4 w-4" />
                Save as Transaction
              </Button>
              <Button variant="outline" onClick={() => toast.info("You can edit the extracted fields directly in this panel before saving.")}>
                <ZoomIn className="h-4 w-4" />
                Edit Before Saving
              </Button>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950/40 dark:text-slate-300">
              <div className="flex items-center gap-2 font-semibold">
                <FileImage className="h-4 w-4 text-assistant" />
                OCR preview notes
              </div>
              <p className="mt-2">Vendor name and GST amount are editable because the current OCR backend returns amount, date, category, and raw text most reliably.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function normalizeDate(value) {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const slash = value.match(/^(\d{2})[/-](\d{2})[/-](\d{4})$/);
  if (slash) return `${slash[3]}-${slash[2]}-${slash[1]}`;
  return "";
}
